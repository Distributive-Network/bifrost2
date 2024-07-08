from .compute_for import compute_for
from .job import Job

sub_classes = {
    'Job': Job,
}

__all__ = ['compute_for', 'sub_classes']

