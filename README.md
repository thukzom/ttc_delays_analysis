# TTC Bus Delays

**What 207,229 published bus delays say about why Toronto buses don't show up.**

Live page → **https://thukzom.github.io/ttc_delays_analysis/**

---

## Why I built this

I rely entirely on the TTC to get anywhere. No car, no alternative — if the bus
doesn't come, I don't go.

So I've spent a lot of my life standing at a stop with no idea when, or whether,
anything is going to arrive. Some of it is the ordinary kind: the bus is fifteen
minutes late and you wait and you're late. Some of it is worse. A bus that runs
*early* pulls away before you get there, and it doesn't matter that you left on
time. A bus that's already full drives straight past you while you're standing
there with your arm out. Either way you're in the same spot, watching the time
you carefully planned for disappear, with nothing to do but wait and hope the
next one is different.

What got to me wasn't the waiting. It was the not knowing — no explanation, no
sense of whether this was bad luck or completely normal, no way to plan around
something I couldn't predict.

It turns out the TTC publishes a record of every delay on its network, going back
to 2014. So instead of guessing, I went and looked.

## What I found

**207,229 delays between 2014 and 2024, adding up to 66,579 hours of lost
service** — the equivalent of a bus route standing still for 7.6 straight years.
The typical delay is 11 minutes. The average is 19, which tells you the long ones
pull hard on the mean.

**The biggest cause of lost time is the one that almost never happens.**
Diversions account for 30% of every hour lost, from just 5.7% of incidents —
because when a route gets diverted it stays diverted for an average of **103
minutes**. Mechanical failures are the opposite: they're the most common thing
that goes wrong, 36% of all incidents, but they average 13 minutes each.

Rank causes by how often they happen and you'd conclude the TTC has a maintenance
problem. Rank them by hours actually lost and the picture changes completely.

| Cause | Share of lost time | Share of incidents | Average length |
|---|---:|---:|---:|
| Diversion | 30.3% | 5.7% | 103 min |
| Mechanical | 24.0% | 35.8% | 13 min |
| Operations – Operator | 14.5% | 19.5% | 14 min |
| General Delay | 6.3% | 5.3% | 23 min |

**Nine of the ten worst locations are subway stations**, not intersections.
Kennedy, Pioneer Village, Kipling, Eglinton, Wilson, Finch. Delays concentrate
where buses meet the subway — at the interchanges where dozens of routes converge
on limited platform and layover space. I expected traffic. What the data shows is
congestion at the transfer points.

**The worst hour is 3pm, not rush hour.** 16,358 delays begin between 3 and 4pm —
about 1.7 times the 8am figure. School dismissal and the beginning of the evening
peak land on top of each other, and afternoon service absorbs it worse than the
morning does.

## What this data can't tell you

Worth being straight about, because two of the three things that frustrate me
most aren't in here at all.

- **Early departures aren't recorded.** A bus that leaves ahead of schedule is
  arguably worse for a rider than a late one — you miss it entirely — but the
  dataset only logs delays.
- **Pass-bys aren't recorded.** A full bus that doesn't stop isn't a delay in the
  TTC's accounting. To the person left standing there it is the whole problem.
- **These are the TTC's own records**, entered by staff, and the categories are
  theirs. "Operations – Operator" covers a lot of ground.
- **Time lost is service time, not rider time.** One diversion on a busy route at
  5pm affects far more people than the same diversion at midnight, and nothing
  here weights for that.

So this measures what the agency counts, which is not the same as what riders
experience. That gap is itself worth knowing about.

## The messy part

The genuinely hard problem in this dataset is that **locations are typed by hand**.
The same corner shows up as:

```
JANE AND FINCH          Jane & Finch
FINCH AVE AT JANE ST    jane st. / finch ave.
```

Four rows, one place. Left alone, the busiest intersections in the city split
across several spellings and never make it into a ranking at all — the top of the
list ends up showing whichever spelling happened to be most popular, not whichever
place is actually worst.

`normalize_location()` collapses them in three steps:

1. upper-case and strip punctuation, so casing and full stops stop mattering
2. remove street-type words (`ST`, `AVE`, `RD`…), so `JANE ST` matches `JANE`
3. **sort the two street names alphabetically**, so `JANE & FINCH` and
   `FINCH & JANE` become the same key

Step three is the one that's easy to miss and does most of the work. Across the
full dataset this reduces the raw location text to 24,567 distinct places.

Other judgement calls:

- **Delays under 1 minute or over 10 hours are dropped.** A zero-minute row is a
  logged event with no service impact; a 900-minute bus delay is a typing error.
- **Unparseable times become blank, not midnight.** Some rows have a time like
  `"n/a"`. Defaulting those to zero would invent a huge fake spike at midnight.
- **Dates are parsed per value**, because the archives mix `2019-04-13` and
  `13/04/2019` in the same column. Forcing one format silently mangles half of them.
- **Causes are ranked by hours lost, not by frequency** — as the table above shows,
  those give completely different answers.

## How it works

| File | What it is |
|---|---|
| `analyze.py` | the whole pipeline — downloads, cleans, summarises, writes `data.json` |
| `index.html` | the page that reads `data.json` and draws the charts |
| `data.json` | the output |
| `run_in_colab.ipynb` | the same analysis, runnable in a browser with nothing installed |

No build step, no server, no scheduled jobs. `analyze.py` asks the City's
open-data catalogue which files exist rather than hardcoding URLs, so it keeps
working when a new year is published.

## Reproducing it

```bash
python3 -m pip install -r requirements.txt

python3 analyze.py --selftest      # checks the cleaning logic, downloads nothing
python3 analyze.py --since 2023    # recent years, a few minutes
python3 analyze.py                 # everything from 2014, ~15 minutes
```

The self-test asserts that all four spellings of Jane & Finch collapse to one
label, that bad dates and zero-minute rows are dropped, and that unparseable
times don't become midnight.

For a browser-only run with nothing to install, open `run_in_colab.ipynb` in
[Google Colab](https://colab.research.google.com) and run the cells in order.

## Data source

[City of Toronto Open Data — TTC Bus Delay Data](https://open.toronto.ca/dataset/ttc-bus-delay-data/),
published monthly under the
[Open Government Licence – Toronto](https://open.toronto.ca/open-data-licence/).

An independent project. Not affiliated with or endorsed by the TTC.
