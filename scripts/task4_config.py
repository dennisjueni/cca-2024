USER = "ubuntu"
from enum import Enum

MEMCACHED = "memcache-server"
NUM_THREADS_MEMCACHED = 4


class JobEnum(Enum):
    RADIX = "radix"
    BLACKSCHOLES = "blackscholes"
    CANNEAL = "canneal"
    DEDUP = "dedup"
    FERRET = "ferret"
    FREQMINE = "freqmine"
    VIPS = "vips"
    SCHEDULER = "scheduler"
    MEMCACHED = "memcached"


DOCKERIMAGES = {
    JobEnum.BLACKSCHOLES: "anakli/cca:parsec_blackscholes",
    JobEnum.CANNEAL: "anakli/cca:parsec_canneal",
    JobEnum.DEDUP: "anakli/cca:parsec_dedup",
    JobEnum.FERRET: "anakli/cca:parsec_ferret",
    JobEnum.FREQMINE: "anakli/cca:parsec_freqmine",
    JobEnum.RADIX: "anakli/cca:splash2x_radix",
    JobEnum.VIPS: "anakli/cca:parsec_vips",
}

NR_THREADS = {
    JobEnum.BLACKSCHOLES: 4,
    JobEnum.CANNEAL: 4,
    JobEnum.DEDUP: 4,
    JobEnum.FERRET: 4,
    JobEnum.FREQMINE: 4,
    JobEnum.RADIX: 4,
    JobEnum.VIPS: 4,
}

CPU_CORES = {
    JobEnum.BLACKSCHOLES: [2, 3],
    JobEnum.CANNEAL: [2, 3],
    JobEnum.DEDUP: [2, 3],
    JobEnum.FERRET: [2, 3],
    JobEnum.FREQMINE: [2, 3],
    JobEnum.RADIX: [2, 3],
    JobEnum.VIPS: [2, 3],
}

sudo_command = f"sudo usermod -a -G docker {USER}"
