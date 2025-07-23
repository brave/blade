# Note:   REST API Server, useful for external async calls from mobile devices
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   09/03/2023

import threading
import time

from flask import Flask

from libs import constants
from libs import logger as blade_logger


class RestAwaitApp:

    def __init__(self, host="0.0.0.0", port=5100):
        self.app = Flask(__name__)
        self.host = host
        self.port = port
        self.continue_execution = None
        self.__setup_routes()
        threading.Thread(target=self.__run_flask_app, daemon=True).start()

    def __setup_routes(self):

        @self.app.route("/")
        def root():
            return "<p>I am BLaDE REST Await service and I am up and running!</p>", 200

        @self.app.route("/continue")
        def continue_execution():

            if self.continue_execution is None:
                print(
                    "Error: No await event is set! You need to call set_await() first.",
                    flush=True,
                )
                return (
                    "<p>Error: No await event is set! You need to call set_await() first.</p>",
                    400,
                )

            else:
                print("Continue execution!", flush=True)
                self.continue_execution.set()
                self.continue_execution = None
                return "<p>OK</p>", 200

    def __run_flask_app(self):
        print("Starting REST Await service...", flush=True)
        self.app.run(host=self.host, port=self.port)

    def set_await(self, timeout=None):
        if self.continue_execution is not None:
            blade_logger.logger.error(
                "Error: An await event is already set. You need to call continue_execution() first."
            )
            return False

        print(
            f"Setting await event with timeout={timeout} seconds.", flush=True)
        self.continue_execution = threading.Event()
        event_set = self.continue_execution.wait(timeout=timeout)
        if event_set == False:
            print(
                f"Warning: Timeout reached while waiting for await event. Timeout={timeout} seconds.",
                flush=True,
            )
            return False

        return True


if __name__ == "__main__":
    # Run rest_await server and wait for a request to continue execution.
    # Only used for testing purposes.

    app = RestAwaitApp()
    time.sleep(constants.REST_AWAIT_SERVER_WAIT_TIME_AFTER_STARTING)
    app.set_await()
    print("Continue execution!", flush=True)
