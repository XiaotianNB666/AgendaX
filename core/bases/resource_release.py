from abc import ABC, abstractmethod

class ResourceReleasable(ABC):
    @abstractmethod
    def release_resource(self):
        pass

    def register_release(self):
        RESOURCE_RELEASE.append(self)

RESOURCE_RELEASE: list[ResourceReleasable] = []