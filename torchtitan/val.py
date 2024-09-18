import gc
import os
import time
from typing import List

import torch
from torch.distributed import FileStore
from torch.nn.functional import cross_entropy

from torchtitan.checkpoint import TrainState
from torchtitan.utils import common_utils as utils
from torchtitan.utils.dataset_utils import create_fresh_file_store


def loss_fn(pred, labels):
    return cross_entropy(pred.flatten(0, 1), labels.flatten(0, 1))


BASE_VALIDATION_SYNC_STORE_PATH = "/tmp/validation_sync_store_step_"


def sync_val_end(
    end_of_validation_store: FileStore, process_ids: List[str], dp_rank: int
):
    end_of_validation_store.set(str(dp_rank), "valfin")
    end_of_validation_store.wait(process_ids)
    return True


def validate(
    model,
    data_loader,
    logger,
    metric_logger,
    parallel_dims,
    gpu_memory_monitor,
    data_loading_times,
    time_last_log,
    color,
    train_step,  # for aim tracking of evaluation to be tracked correctly
    num_flop_per_token,
    gpu_peak_flops,
    dp_rank,
    world_size,
    enable_compiled_autograd,
):
    end_of_validation_path = f"{BASE_VALIDATION_SYNC_STORE_PATH}{train_step}"
    end_of_validation_store = create_fresh_file_store(
        end_of_validation_path, world_size
    )
    eval_state = TrainState()
    total_n_tokens = 0
    total_loss = 0
    total_perplexity = 0
    cnt = 0
    total_eval_time = 0
    loss = None

    train_context = utils.get_train_context(
        parallel_dims.loss_parallel_enabled,
        enable_compiled_autograd,
    )

    process_ids = [str(rank) for rank in range(world_size)]

    model.eval()

    eval_state.step = 0
    val_data_iterator = iter(data_loader)
    while True:
        batch = next(val_data_iterator, None)

        if not batch:
            sync_val_end(end_of_validation_store, process_ids, dp_rank)
            break

        eval_state.step += 1

        data_load_start = time.perf_counter()
        input_ids, labels = batch

        n_tokens_in_curr = labels.numel()
        input_ids = input_ids.cuda()
        labels = labels.cuda()

        with train_context():
            with torch.no_grad():
                if end_of_validation_store.num_keys() > 1:
                    continue
                else:
                    total_n_tokens += n_tokens_in_curr  # we only add to the total tokens if we actually run a prediction
                    data_loading_times.append(time.perf_counter() - data_load_start)
                    pred = model(input_ids)
                    loss = loss_fn(pred, labels)
                    del pred

        time_delta = time.perf_counter() - time_last_log
        total_eval_time += time_delta
        total_loss += loss
        total_perplexity += 2**loss
        cnt += 1
        wps = n_tokens_in_curr / (time_delta * parallel_dims.model_parallel_size)
        mfu = 100 * num_flop_per_token * wps / gpu_peak_flops
        gpu_mem_stats = gpu_memory_monitor.get_peak_stats()

        logger.info(
            "context: val"
            f"{color.cyan}step: {eval_state.step}  "
            f"{color.green}loss: {loss:7.4f}  "
            f"{color.yellow}memory: {gpu_mem_stats.max_reserved_gib:5.2f}GiB"
            f"({gpu_mem_stats.max_reserved_pct:.2f}%)  "
            f"{color.blue}wps: {round(wps):,}  "
            f"{color.magenta}mfu: {mfu:.2f}%{color.reset}"
        )
        time_last_log = time.perf_counter()

    metrics = {
        "val/loss_metrics/global_avg_loss": total_loss / eval_state.step,
        "val/loss_metrics/global_avg_perplexity": total_perplexity / eval_state.step,
        "val/wps": total_n_tokens / total_eval_time,
        "val/mfu(%)": 100
        * num_flop_per_token
        * (total_n_tokens / total_eval_time)
        / gpu_peak_flops,
    }
    # metrics = {
    #     "val/loss_metrics/global_avg_loss": loss,
    #     "val/loss_metrics/global_avg_perplexity": perplexity,
    #     "val/wps": wps,
    #     "val/mfu(%)": mfu,
    #     "val/time_metrics/end_to_end(s)": time_end_to_end,
    #     "val/time_metrics/data_loading(s)": time_data_loading,
    #     "val/time_metrics/data_loading(%)": time_data_loading_pct,
    #     "val/memory/max_active(GiB)": gpu_mem_stats.max_active_gib,
    #     "val/memory/max_active(%)": gpu_mem_stats.max_active_pct,
    #     "val/memory/max_reserved(GiB)": gpu_mem_stats.max_reserved_gib,
    #     "val/memory/max_reserved(%)": gpu_mem_stats.max_reserved_pct,
    #     "val/memory/num_alloc_retries": gpu_mem_stats.num_alloc_retries,
    #     "val/memory/num_ooms": gpu_mem_stats.num_ooms,
    # }
    metric_logger.log(metrics, step=train_step)

    if loss:
        del loss

    if os.path.exists(end_of_validation_path) and dp_rank == 0:
        os.remove(end_of_validation_path)
        logger.info("removed the store file")
    else:
        logger.info("no store file exists")
    del val_data_iterator, data_loader, end_of_validation_store

    gc.collect()
    model.train()
