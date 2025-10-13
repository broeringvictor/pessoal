from typing import Any, Dict, NamedTuple
from pydantic import BaseModel, Field, model_validator
import json

class ResponsePayload(NamedTuple):
    code: int
    success: bool
    message: str
    data: Any

class Response(BaseModel):
    """Classe base da Camada de Aplicação para representar respostas de operações de casos de uso.
    
    Atributos:
        code (int): Código HTTP da resposta.
        success (bool | None): Indica se a operação foi bem-sucedida; se None, será derivado de 'code'.
        message (str): Mensagem associada à resposta.
        data (Any): Dados associados à resposta.
    """
    code: int = Field(default=200)
    success: bool | None = Field(default=None)
    message: str = Field(default="")
    data: Any = Field(default=None)

    @model_validator(mode="after")
    def _derive_success_and_validate(self) -> "Response":
        self._validate_http_status_code(self.code)
        if self.success is None:
            self.success = 200 <= self.code < 300
        return self

    @staticmethod
    def _validate_http_status_code(http_status_code: int) -> None:
        if not isinstance(http_status_code, int):
            raise TypeError("HTTP status code must be an integer.")
        if http_status_code < 100 or http_status_code > 599:
            raise ValueError("HTTP status code must be between 100 and 599.")

    @classmethod
    def sucesso(cls, data: Any = None, message: str = "", code: int = 200) -> "Response":
        """Cria uma resposta bem-sucedida (códigos 2xx).

        Exemplo:
            >>> Response.sucesso(data={"identidade_recurso": "123"}, message="OK").to_dict()
            {'code': 200, 'success': True, 'message': 'OK', 'data': {'identidade_recurso': '123'}}
        """
        if not (200 <= code < 300):
            raise ValueError("For 'sucesso', the HTTP status code must be in the 2xx range.")
        return cls(success=True, message=message, data=data, code=code)

    def to_named_tuple(self) -> ResponsePayload:
        return ResponsePayload(
            code=self.code,
            success=bool(self.success),
            message=self.message,
            data=self.data,
        )

    def to_dict(self) -> Dict[str, Any]:
        return self.to_named_tuple()._asdict()

    def to_json(self) -> str:
        return json.dumps(self.to_named_tuple()._asdict(), ensure_ascii=False, default=str)

    def __str__(self) -> str:
        return f"Response(code={self.code}, success={self.success}, message='{self.message}', data={self.data})"
