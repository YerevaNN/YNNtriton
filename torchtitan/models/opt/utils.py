from torchtitan.models.opt import OPT
from transformers import OPTForCausalLM


def get_hf_opt_state_dict_keys_mapping(num_layers: int):
    """
    Get a mapping between state dict keys of different implementations.

    Args:
        num_layers (int): number of transformer layers (blocks).

    Returns:
        dict: mapping between local implementation state dict keys and hf implementation state dict keys

    """
    keys_mapping = {
        "tok_embeddings.weight": "model.decoder.embed_tokens.weight",
        "pos_encoder.weight": "model.decoder.embed_positions.weight",
        # add layer weight mappings here
        "norm.weight": "model.decoder.final_layer_norm.weight",
        "norm.bias": "model.decoder.final_layer_norm.bias",
        "output.weight": "lm_head.weight",
    }
    for layer in range(num_layers):
        keys_mapping.update(
            {
                f"layers.{layer}.attention.wq.weight": f"model.decoder.layers.{layer}.self_attn.q_proj.weight",
                f"layers.{layer}.attention.wq.bias": f"model.decoder.layers.{layer}.self_attn.q_proj.bias",
                f"layers.{layer}.attention.wk.weight": f"model.decoder.layers.{layer}.self_attn.k_proj.weight",
                f"layers.{layer}.attention.wk.bias": f"model.decoder.layers.{layer}.self_attn.k_proj.bias",
                f"layers.{layer}.attention.wv.weight": f"model.decoder.layers.{layer}.self_attn.v_proj.weight",
                f"layers.{layer}.attention.wv.bias": f"model.decoder.layers.{layer}.self_attn.v_proj.bias",
                f"layers.{layer}.attention.wo.weight": f"model.decoder.layers.{layer}.self_attn.out_proj.weight",
                f"layers.{layer}.attention.wo.bias": f"model.decoder.layers.{layer}.self_attn.out_proj.bias",
                f"layers.{layer}.feed_forward.w1.weight": f"model.decoder.layers.{layer}.fc1.weight",
                f"layers.{layer}.feed_forward.w1.bias": f"model.decoder.layers.{layer}.fc1.bias",
                f"layers.{layer}.feed_forward.w2.weight": f"model.decoder.layers.{layer}.fc2.weight",
                f"layers.{layer}.feed_forward.w2.bias": f"model.decoder.layers.{layer}.fc2.bias",
                f"layers.{layer}.attention_norm.weight": f"model.decoder.layers.{layer}.self_attn_layer_norm.weight",
                f"layers.{layer}.attention_norm.bias": f"model.decoder.layers.{layer}.self_attn_layer_norm.bias",
                f"layers.{layer}.ffn_norm.weight": f"model.decoder.layers.{layer}.final_layer_norm.weight",
                f"layers.{layer}.ffn_norm.bias": f"model.decoder.layers.{layer}.final_layer_norm.bias",
            }
        )

    return keys_mapping


def load_opt_weights(model: OPT, weights_path: str, source: str):
    """
    write docs
    """
    if source == "huggingface":
        hf_model = OPTForCausalLM.from_pretrained(weights_path)
        keys_mapping = get_hf_opt_state_dict_keys_mapping(model.n_layers)
        hf_state_dict = hf_model.state_dict()
        corrected_state_dict = {}
        for key, value in keys_mapping.items():
            corrected_state_dict[key] = hf_state_dict[value]

        model.load_state_dict(corrected_state_dict)
    else:
        raise NotImplementedError
