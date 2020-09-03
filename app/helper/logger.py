import logging
import traceback
import sys
import rapidjson
import structlog
from structlog.contextvars import merge_contextvars
from structlog.contextvars import bind_contextvars


def add_fields(**kwargs):
    """
    Add key-value pairs to our homemade logger
    e.g.
        >>> bind_contextvars(a=1, b=2)
        >>> # Then use loggers as per normal
        >>> log.msg("hello")
        a=1 b=2 event='hello'
    Full documentation: https://www.structlog.org/en/stable/contextvars.html
    """
    bind_contextvars(**kwargs)


class StackDriverRenderer(object):
    def __init__(self, service_name=None):
        self.service_name = service_name

    def __call__(self, _, method, event_dict):
        if self.service_name:
            event_dict['serviceContext'] = {'service': self.service_name}

        # rename event to msg
        if 'event' in event_dict:
            event_dict['message'] = event_dict['event']
            del event_dict['event']

        # Required by stackdriver to display level of error accordingly
        event_dict.setdefault("severity", method)

        if method == 'error' or method == 'critical':
            # Enable display of this error in 'Error reporting' in GCP
            event_dict['@type'] = 'type.googleapis.com/google.devtools.clouderrorreporting.v1beta1.ReportedErrorEvent'
            if sys.exc_info()[0]:
                # check if an exception exist https://docs.python.org/2/library/sys.html#sys.exc_info
                event_dict['stack_trace'] = traceback.format_exc()

        return event_dict


def init_logger(service_name='wellbore-ddms'):

    """ Initialize structlog with following configuration:
    - Make logs compatible with Stackdriver
    - if dev_mode, display stacktrace out of json item
    Return initialized root logger
    """

    structlog.configure(
        processors=[
            StackDriverRenderer(service_name=service_name),
            merge_contextvars,
            # structlog.processors.KeyValueRenderer(),
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            # structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(serializer=rapidjson.dumps)
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    my_logger = structlog.getLogger('ddms-app')

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(message)s')
    ch.setFormatter(formatter)
    my_logger.addHandler(ch)

    std_ddms_app = logging.getLogger('ddms-app')
    std_ddms_app.propagate = False

    return my_logger
