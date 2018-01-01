class PhantomStructures(object):
    path = ''

    def __init__(self, camera, path=''):
        super(PhantomStructures, self).__setattr__('camera', camera)
        if path:
            super(PhantomStructures, self).__setattr__('path', self.path + path)

    def __getattr__(self, item):
        if self.path:
            return PhantomStructures(self.camera, self.path + '.' + item)
        else:
            return PhantomStructures(self.camera, item)

    def __setattr__(self, key, value):
        cmd = 'set {}.{} {}'.format(self.path, key, value)
        self.camera.ask(cmd)

    def __dir__(self):
        try:
            return self._get().keys()
        except AttributeError:
            return dir(self._get())

    def _get(self):
        cmd = 'get {}'.format(self.path if self.path else '*')
        return self.camera.ask(cmd)

    def __int__(self):
        return int(self._get())

    def __float__(self):
        return float(self._get())

    def __str__(self):
        return str(self._get())

    def __repr__(self):
        return self.__str__()
