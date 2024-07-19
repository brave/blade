# Note:   Utility functions for parsing command line arguments.
# Author: Stefanos Laskaridis (stefanos@brave.com

import os

HOME = os.path.expanduser("~")


def parse_common_args(parser):
    # Common executioin arguments
    parser.add_argument(
        "-d", "--device", required=True, help="Android device to be used."
    )

    parser.add_argument(
        "-m",
        "--model",
        required=True,
        help="Model to be used during evaluation. In case of LLMFarmEval, this is the path to the model folder. In case of MLCChat, this is the model name.",
    )

    parser.add_argument(
        "-r",
        "--runs",
        type=int,
        required=False,
        default=3,
        help="Number of evaluation runs to be executed.",
    )

    parser.add_argument(
        "-desc",
        "--description",
        required=False,
        default="",
        help="Description of the experiment.",
    )

    # Input arguments
    parser.add_argument(
        "-cf",
        "--conversation-from",
        type=int,
        required=False,
        default=0,
        help="Starting index for choosing conversations to be evaluated.",
    )

    parser.add_argument(
        "-ct",
        "--conversation-to",
        type=int,
        required=False,
        default=49,
        help="Ending index for choosing conversations to be evaluated.",
    )

    # LLM specific arguments
    parser.add_argument(
        "--max-gen-len", type=int, help="Maximum length of the generated response."
    )
    parser.add_argument(
        "--max-context-size", type=int, help="Maximum length of the context."
    )
    parser.add_argument(
        "--prefill-chunk-size", type=int, help="Chunk size for prefilling the context."
    )
    parser.add_argument(
        "--input-token-batching",
        type=int,
        help="Batch size for generation (applicable only to llama).",
    )

    # Generation specific arguments
    parser.add_argument("--temperature", type=float,
                        help="Temperature for sampling.")
    parser.add_argument("--top-p", type=float, help="Top-p for sampling.")
    parser.add_argument("--top-k", type=int, help="Top-k for sampling.")
    parser.add_argument(
        "--repeat-penalty", type=float, help="Repeat penalty for sampling."
    )
    parser.add_argument(
        "--loglevel", default="INFO", help="Set the log level for the experiment."
    )


def parse_ios_args(parser):
    parser.add_argument(
        "-a",
        "--app",
        required=True,
        choices=["LLMFarmEval", "MLCChat", "MLCChat++"],
        help="LLM App to be evaluated.",
    )

    parser.add_argument(
        "-o",
        "--output",
        required=False,
        default=os.path.join(HOME, "ssd/llm-eval-ios"),
        help="Output folder for storing the measurements.",
    )

    # Generation compute arguments
    parser.add_argument(
        "--cpu",
        default=False,
        action="store_true",
        help="GPU to be used for generation.",
    )
    parser.add_argument(
        "--n-threads",
        type=int,
        default=None,
        help="Number of threads to be used for generation.",
    )


def parse_android_args(parser):
    parser.add_argument(
        "-b",
        "--brightness",
        type=int,
        required=False,
        default=50,
        help="Set the device's brightness (0-255).",
    )

    parser.add_argument(
        "-a",
        "--app",
        required=True,
        choices=["LlamaCpp", "MLCChat", "MLCChat++"],
        help="LLM App to be evaluated.",
    )

    parser.add_argument(
        "-o",
        "--output",
        required=False,
        default=os.path.join(HOME, "ssd/llm-eval-android"),
        help="Output folder for storing the measurements.",
    )

    parser.add_argument(
        "-t",
        "--n-threads",
        type=int,
        default=1,
        help="Number of threads to be used for generation on CPU.",
    )
