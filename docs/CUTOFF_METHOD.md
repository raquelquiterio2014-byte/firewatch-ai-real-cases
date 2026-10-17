# BOUNDED_DELIVERY_V1

The portal delivery stamp is a timezone-unspecified civil datetime. The code uses UTC only as a calculation origin, not as an assertion that the provider timestamp is UTC.

1. Earliest possible UTC delivery = displayed stamp − 14 hours.
2. Latest possible UTC delivery = displayed stamp + 12 hours.
3. Map-production date is treated as a UTC day because its table is explicitly headed UTC.
4. Conservative lower bound = maximum of observation UTC, production-day UTC start and earliest possible delivery.
5. Conservative upper bound = maximum of production-day UTC end and latest possible delivery.
6. Admit conditionally only when the entire conservative interval is at or before the cutoff, file integrity matches, and the AI technical review matches the dataset hash.

The use of the maximum for the upper bound deliberately withholds records longer when production and portal metadata are ambiguous. This is an explicit research policy, not a measured availability bound. It assumes the portal card describes the downloaded version. Neither that historical version relationship nor actual responder receipt has been verified.

At the primary cutoff of 17 July 2022 12:00 UTC, P01's upper bound is 17 July 07:23:29 UTC, while P02's is 18 July 00:00 UTC and P03's is 18 July 05:37:44 UTC. Thus only P01 enters the conditional research analysis. Earlier and later checkpoints test exclusion and inclusion without introducing later exposure claims into the primary model input.

Strict mode excludes every pilot record because original availability is not independently verified. A human research acceptance cannot change that eligibility.
