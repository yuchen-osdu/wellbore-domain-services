class RecordNotFoundException(Exception):
    """ Raised when specified Record does not exist """
    pass


class NoDataException(Exception):
    """ Raised when asking data for a Record that doesn't have any data """
    pass


class NoBulkException(Exception):
    """ Raised when asking data for a Record that doesn't have bulkURI """
    pass


class InvalidBulkException(Exception):
    """ Raised when asking data for a Record that have an invalid bulkURI """
    pass


class UnknownChannelsException(Exception):
    """ Raised when unknown channel  """
    pass
