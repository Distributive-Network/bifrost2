class Env:
    def __init__(self):
        self.env = {}
    def convert_to_arguments(self):
        args = []
        for env_key in self.env:
            args.append(f"{env_key}={self.env[env_key]}")
        return args
