from .compute_for import compute_for_maker
from .job import job_maker
from .result_handle import result_handle_maker 

sub_classes = {
    'Job': job_maker,
    'ResultHandle': result_handle_maker,
}

__all__ = ['compute_for_maker', 'sub_classes']

