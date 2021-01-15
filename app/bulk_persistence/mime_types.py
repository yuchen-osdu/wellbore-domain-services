from typing import Generator, List, NamedTuple


class MimeType(NamedTuple):
    """ expected always lower case """

    type: str
    extension: str
    alternative_types: List[str] = []

    def match(self, str_value: str) -> bool:
        normalized_value = str_value.lower()
        return any(
            (
                normalized_value == a_type
                for a_type in [self.type] + self.alternative_types
            )
        ) or normalized_value.replace(".", "") == self.extension.replace(
            ".", ""
        )


class MimeTypes:
    """
    define mime types used in the application
    Note: May be use https://docs.python.org/3/library/mimetypes.html
        mimetypes.add_type('application/x-parquet', '.parquet')
    """

    PARQUET = MimeType(
        type="application/x-parquet",
        extension=".parquet",
        alternative_types=["application/parquet"],
    )  # because https://tools.ietf.org/html/rfc6838#section-3.4

    FEATHER = MimeType(
        type="application/x-feather",
        extension=".feather",
        alternative_types=["application/feather"],
    )

    JSON = MimeType(type="application/json", extension=".json")

    MSGPACK = MimeType(
        type="application/x-msgpack",
        extension=".msgpack",
        alternative_types=[
            "application/msgpack",
            "application/messagepack",
            "application/x-messagepack",
            "application/vnd.messagepack",
            "application/vnd.msgpack",
        ],
    )

    @classmethod
    def types(cls) -> Generator[MimeType, None, None]:
        """ enumerate all type """
        for _, t in cls.__dict__.items():
            if isinstance(t, MimeType):
                yield t

    @classmethod
    def from_str(cls, value: str) -> MimeType:
        for t in cls.types():
            if t.match(value):
                return t
        raise ValueError(f"{value} does not match any supported mime types")

    # todo add guess_type(path_like) method ?
