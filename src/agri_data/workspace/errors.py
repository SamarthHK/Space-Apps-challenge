class WorkspaceUnavailable(Exception):
    pass


class WorkspaceError(Exception):
    def __init__(self, status, code, message):
        self.status, self.code, self.message = status, code, message
        super().__init__(message)
