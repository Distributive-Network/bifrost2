def result_handle_maker(super_class):
    class ResultHandle(super_class):
        def __str__(self):
            return str(self.values())

        def __repr__(self):
            return self.__str__()
    return ResultHandle

