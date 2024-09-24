# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from torchtitan.tokenizers.tokenizer.custom import CustomTokenizer
from torchtitan.tokenizers.tokenizer.sentencepiece import SentencePieceTokenizer
from torchtitan.tokenizers.tokenizer.tiktoken import TikTokenizer
from torchtitan.tokenizers.tokenizer.tokenizer import Tokenizer
from torchtitan.logging import logger


def build_tokenizer(tokenizer_type: str, tokenizer_path: str) -> Tokenizer:
    logger.info(f"Building tokenizer of type {tokenizer_type}, locally from {tokenizer_path}")

    if tokenizer_type == "sentencepiece":
        return SentencePieceTokenizer(tokenizer_path)
    elif tokenizer_type == "tiktoken":
        return TikTokenizer(tokenizer_path)

    return CustomTokenizer(tokenizer_path)
