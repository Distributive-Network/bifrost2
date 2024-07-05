from .compute_for import compute_for
from .job import Job

inheritance_hooks = {
    'Job': Job,
}

__all__ = ['compute_for', 'inheritance_hooks']

