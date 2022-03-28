
class RequestedCurvesError(Exception):
    """ Raised if requested curves don't exist in associated WellLog """
    pass


class ComputationRunningError(Exception):
    """ Raised if computation of bulk statistics are already running """
    pass


class StatisticsNotFoundError(Exception):
    """ Raised if requestes bulk statistics does not exist"""
