from genai4fuzz.utils.singleton import SingletonMeta


class Config(metaclass=SingletonMeta):
    def __init__(self) -> None:
        self.results_dir: str = "results"
