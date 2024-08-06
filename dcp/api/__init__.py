from .compute_for import compute_for_maker
from .job import job_maker
from .result_handle import result_handle_maker 
from .job_serializers import Serializers
from .job_env import Env
from .job_modules import Modules
from .job_fs import JobFS

sub_classes = {
    'Job': job_maker,
    'ResultHandle': result_handle_maker,
    'Serializers': Serializers,
    'Env': Env,
    'Modules': Modules
}

__all__ = ['compute_for_maker', 'sub_classes', 'JobFS']

