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


DOCKERIMAGES = {
    JobEnum.BLACKSCHOLES: "anakli/cca:parsec_blackscholes",
    JobEnum.CANNEAL: "anakli/cca:parsec_canneal",
    JobEnum.DEDUP: "anakli/cca:parsec_dedup",
    JobEnum.FERRET: "anakli/cca:parsec_ferret",
    JobEnum.FREQMINE: "anakli/cca:parsec_freqmine",
    JobEnum.RADIX: "anakli/cca:splash2x_radix",
    JobEnum.VIPS: "anakli/cca:parsec_vips",
}

sudo_command = f"sudo usermod -a -G docker {USER}"
# TODO : Need to run this command on the host machine
