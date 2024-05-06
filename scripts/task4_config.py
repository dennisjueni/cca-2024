USER = "ubuntu"
from enum import Enum

MEMCACHED = "memcache-server"
NUM_THREADS_MEMCACHED = 4


class JobEnum(Enum):
    # MEMCACHED = "memcached"
    BLACKSCHOLES = "blackscholes"
    CANNEAL = "canneal"
    DEDUP = "dedup"
    FERRET = "ferret"
    FREQMINE = "freqmine"
    RADIX = "radix"
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
    JobEnum.BLACKSCHOLES: 3,
    JobEnum.CANNEAL: 3,
    JobEnum.DEDUP: 3,
    JobEnum.FERRET: 3,
    JobEnum.FREQMINE: 3,
    JobEnum.RADIX: 3,
    JobEnum.VIPS: 3,
}

sudo_command = f"sudo usermod -a -G docker {USER}"
