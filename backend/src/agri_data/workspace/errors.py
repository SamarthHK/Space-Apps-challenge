class WorkspaceUnavailable(Exception):
    pass


class WorkspaceError(Exception):
    def __init__(self, status, code, message, *, headers=None):
        self.status, self.code, self.message = status, code, message
        self.headers = headers
        super().__init__(message)
