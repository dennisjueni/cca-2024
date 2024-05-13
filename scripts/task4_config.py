USER = "ubuntu"
from enum import Enum

MEMCACHED = "memcache-server"
NUM_THREADS_MEMCACHED = 4


class JobEnum(Enum):
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


# CHANGE_THRESHOLD * 10 is the QPS at which we will switch from 1 to 2 cores or vice versa
CHANGE_THRESHOLD = 5000
THRESHOLDS = {
    JobEnum.BLACKSCHOLES: CHANGE_THRESHOLD,
    JobEnum.CANNEAL: CHANGE_THRESHOLD,
    JobEnum.DEDUP: CHANGE_THRESHOLD - 500,
    JobEnum.FERRET: CHANGE_THRESHOLD - 1000,
    JobEnum.FREQMINE: CHANGE_THRESHOLD,
    JobEnum.RADIX: CHANGE_THRESHOLD,
    JobEnum.VIPS: CHANGE_THRESHOLD,
}
