class AsgiError(Exception):
    pass


class InvalidMessageError(AsgiError):
    def __init__(self, message_type: str):
        super().__init__(f"Invalid message type '{message_type}'")
        self.type = message_type
