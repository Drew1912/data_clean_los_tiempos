class InputError(Exception):
    def __init__(self, code, message, status=400, field=None):
        super().__init__(message)
        self.code, self.message, self.status, self.field = code, message, status, field

    def payload(self):
        result = {"codigo": self.code, "mensaje": self.message}
        if self.field:
            result["campo"] = self.field
        return {"error": result}


class FileError(InputError):
    """Error de estructura de una fuente; se informa sin descartar las otras."""
