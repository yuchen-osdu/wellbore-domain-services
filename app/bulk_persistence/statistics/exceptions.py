
class RequestedCurvesError(Exception):
    """ Raised if requested curves don't exist in associated WellLog """
    pass


class ComputationRunningError(Exception):
    """ Raised if computation of bulk statistics are already running """
    pass


class StatisticsNotFoundError(Exception):
    """ Raised if requested bulk statistics does not exist"""


class ComputationNotCompleteError(Exception):
    """ Raised if computation of requested bulk statistics is not finished yet """
    pass
