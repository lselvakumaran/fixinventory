from resotolib.logger import log
from dataclasses import dataclass
from typing import ClassVar, Dict
from resotolib.graph import Graph

from resotolib.baseresources import (
    BaseAccount,
    BaseRegion,
    BaseInstance,
    BaseNetwork,
    BaseVolume,
    BaseLoadBalancer,
    InstanceStatus,
    VolumeStatus,
)


@dataclass(eq=False)
class RandomAccount(BaseAccount):
    kind: ClassVar[str] = "random_account"

    def delete(self, graph: Graph) -> bool:
        return NotImplemented


@dataclass(eq=False)
class RandomRegion(BaseRegion):
    kind: ClassVar[str] = "random_region"

    def delete(self, graph: Graph) -> bool:
        """Regions can usually not be deleted so we return NotImplemented"""
        return NotImplemented


@dataclass(eq=False)
class RandomResource:
    """A class that implements the abstract method delete() as well as update_tag()
    and delete_tag().

    delete() must be implemented. update_tag() and delete_tag() are optional.
    """

    kind: ClassVar[str] = "random_resource"

    def delete(self, graph: Graph) -> bool:
        """Delete a resource in the cloud"""
        log.debug(f"Deleting resource {self.id} in account {self.account(graph).id} region {self.region(graph).id}")
        return True

    def update_tag(self, key, value) -> bool:
        """Update a resource tag in the cloud"""
        log.debug(f"Updating or setting tag {key}: {value} on resource {self.id}")
        return True

    def delete_tag(self, key) -> bool:
        """Delete a resource tag in the cloud"""
        log.debug(f"Deleting tag {key} on resource {self.id}")
        return True


@dataclass(eq=False)
class RandomInstance(RandomResource, BaseInstance):
    kind: ClassVar[str] = "random_instance"
    instance_status_map: ClassVar[Dict[str, InstanceStatus]] = {
        "pending": InstanceStatus.BUSY,
        "running": InstanceStatus.RUNNING,
        "shutting-down": InstanceStatus.BUSY,
        "terminated": InstanceStatus.TERMINATED,
        "stopping": InstanceStatus.BUSY,
        "stopped": InstanceStatus.STOPPED,
    }

    def _instance_status_setter(self, value: str) -> None:
        self._instance_status = self.instance_status_map.get(value, InstanceStatus.UNKNOWN)


RandomInstance.instance_status = property(
    RandomInstance._instance_status_getter, RandomInstance._instance_status_setter
)


@dataclass(eq=False)
class RandomVolume(RandomResource, BaseVolume):
    kind: ClassVar[str] = "random_volume"

    volume_status_map: ClassVar[Dict[str, VolumeStatus]] = {
        "creating": VolumeStatus.BUSY,
        "available": VolumeStatus.AVAILABLE,
        "in-use": VolumeStatus.IN_USE,
        "deleting": VolumeStatus.BUSY,
        "deleted": VolumeStatus.DELETED,
        "error": VolumeStatus.ERROR,
        "busy": VolumeStatus.BUSY,
    }

    def _volume_status_setter(self, value: str) -> None:
        self._volume_status = self.volume_status_map.get(value, VolumeStatus.UNKNOWN)


RandomVolume.volume_status = property(RandomVolume._volume_status_getter, RandomVolume._volume_status_setter)


@dataclass(eq=False)
class RandomNetwork(RandomResource, BaseNetwork):
    kind: ClassVar[str] = "random_network"


@dataclass(eq=False)
class RandomLoadBalancer(RandomResource, BaseLoadBalancer):
    kind: ClassVar[str] = "random_load_balancer"


first_names = [
    "Aada",
    "Aaliyah",
    "Aarav",
    "Aaron",
    "Aaryan",
    "Abhinav",
    "Adele",
    "Aidan",
    "Aino",
    "Alberto",
    "Aleksi",
    "Alexey",
    "Alice",
    "Alva",
    "Alvaro",
    "Amelia",
    "Ananya",
    "Anastasia",
    "Andrei",
    "Angeliki",
    "Anika",
    "Anja",
    "Anna",
    "Anni",
    "Anton",
    "Antonia",
    "Aoi",
    "Aradhya",
    "Aria",
    "Ariel",
    "Arnav",
    "Arthur",
    "Arttu",
    "Artyom",
    "Athanasios",
    "Ava",
    "Avery",
    "Beatriz",
    "Birta",
    "Bjarni",
    "Bjorn",
    "Camille",
    "Carlos",
    "Catalina",
    "Chloe",
    "Chris",
    "Clara",
    "Constanza",
    "Cora",
    "Cristobal",
    "Daiki",
    "Daniela",
    "Devansh",
    "Dhruv",
    "Diego",
    "Dimitrios",
    "Dmitry",
    "Doris",
    "Dylan",
    "Eetu",
    "Einar",
    "Eleni",
    "Elias",
    "Elin",
    "Ella",
    "Elzbieta",
    "Emil",
    "Enzo",
    "Ethan",
    "Evegny",
    "Ewa",
    "Felix",
    "Fernanda",
    "Flo",
    "Grace",
    "Graciela",
    "Gunnar",
    "Guorun",
    "Hannah",
    "Harini",
    "Helga",
    "Hugo",
    "Ida",
    "Ines",
    "Ioannis",
    "Irina",
    "Isak",
    "Ishan",
    "Itai",
    "Ivan",
    "Jade",
    "Jan",
    "Janice",
    "Javiera",
    "Jocelyn",
    "Joel",
    "John",
    "Jonas",
    "Jorge",
    "Jose",
    "Juan",
    "Juho",
    "Julia",
    "Julian",
    "Kaito",
    "Katarzyna",
    "Kenta",
    "Kostantina",
    "Krzysztof",
    "Lars",
    "Lauri",
    "Layla",
    "Lea",
    "Leevi",
    "Lena",
    "Leon",
    "Leonie",
    "Lida",
    "Luca",
    "Lucas",
    "Lucia",
    "Lukas",
    "Magnus",
    "Maja",
    "Manon",
    "Marcin",
    "Marek",
    "Maricel",
    "Marie",
    "Mario",
    "Marlon",
    "Marta",
    "Martina",
    "Matthias",
    "Maxime",
    "Maximilian",
    "Mia",
    "Mikhail",
    "Milan",
    "Misaki",
    "Mitsuki",
    "Miu",
    "Miyu",
    "Moe",
    "Mohamed",
    "Nanami",
    "Naom",
    "Natalia",
    "Nathan",
    "Navita",
    "Navya",
    "Nikita",
    "Noah",
    "Norma",
    "Oceana",
    "Olafur",
    "Olga",
    "Oliver",
    "Oscar",
    "Pablo",
    "Paula",
    "Pranav",
    "Ren",
    "Ricardo",
    "Ridhi",
    "Riko",
    "Rin",
    "Rishika",
    "Ronald",
    "Rosa",
    "Rowena",
    "Raffa",
    "Ryan",
    "Sanvi",
    "Sarah",
    "Sergei",
    "Shaurya",
    "Sho",
    "Shun",
    "Sigurour",
    "Siiri",
    "Silvia",
    "Simon",
    "Sota",
    "Takumi",
    "Tamar",
    "Tatiana",
    "Tejas",
    "Telma",
    "Tim",
    "Tobi",
    "Tomasz",
    "Trisha",
    "Ulhas",
    "Valentina",
    "Valeria",
    "Vanessa",
    "Veeti",
    "Venla",
    "Vicente",
    "Yael",
    "Yu",
    "Yulia",
    "Zoe",
    "Zoey",
    "Zofia",
]


purposes = [
    ["bus", "Business"],
    ["edu", "Education"],
    ["ent", "Entertainment"],
    ["fin", "Finance"],
    ["game", "Gaming"],
    ["gov", "Government"],
    ["news", "News"],
    ["office", "Office"],
    ["misc", "Other"],
    ["priv", "Personal"],
    ["shop", "Shopping"],
    ["soc", "Social"],
    ["sprt", "Sports"],
    ["trvl", "Travel"],
    ["wrk", "Work"],
    ["dev", "Development"],
    ["res", "Research"],
    ["web", "Webserver"],
    ["db", "Database"],
    ["stor", "Storage"],
    ["cloud", "Cloud"],
    ["host", "Hosting"],
]
