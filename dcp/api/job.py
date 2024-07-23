import pythonmonkey as pm

def job_maker(super_class):
    class Job(super_class):
        #def exec(self, *args, **kwargs):
        #    # TODO change behaviour to match spec
        #    #print("overidden by Job hook")

        def wait(self, *args, **kwargs):
            pass

        def on(self, *args):
            if len(args) > 1 and callable(args[1]):
                event_name = args[0]
                event_cb = args[1]
                self.js_ref.on(event_name, event_cb)
            else:
                event_name = args[0]
                def decorator(fn):
                    self.js_ref.on(event_name, fn)
                return decorator
    return Job

