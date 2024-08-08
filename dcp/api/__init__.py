from .compute_for import compute_for_maker
from .compute_do import compute_do_maker
from .job import job_maker
from .result_handle import result_handle_maker 
from .job_fs import JobFS

sub_classes = {
    'Job': job_maker,
    'ResultHandle': result_handle_maker,
}

__all__ = ['compute_for_maker', 'compute_do_maker' 'sub_classes', 'JobFS']

