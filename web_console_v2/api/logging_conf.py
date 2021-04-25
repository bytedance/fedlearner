import os
import logging

LOGGING_CONFIG = {
    'version': 1,
    'root': {
        'handlers': ['console', 'root_file'],
        'level': 'INFO'
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'root_file': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'formatter': 'generic',
            'filename': os.path.join(os.getenv('FEDLEARNER_WEBCONSOLE_LOG_DIR', '.'), 'root.log'),
            'when': 'D',
            'interval': 1,
            'backupCount': 7
        }
    },
    'formatters': {
        'generic': {
            'format': '%(asctime)s [%(process)d] [%(levelname)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
            'class': 'logging.Formatter'
        }
    }
}