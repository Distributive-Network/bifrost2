from .compute_for import compute_for_maker
from .job import Job
from .result_handle import ResultHandle
from .jobfs import JobFS

sub_classes = {
    'Job': Job,
    'ResultHandle': ResultHandle,
}

__all__ = ['compute_for_maker', 'sub_classes', 'JobFS']

