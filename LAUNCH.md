# Launch checklist

About 45 minutes, most of it waiting for downloads. Do the steps in order.
The project is on your Mac at **`Documents/ttc-bus-delays`**.

---

## Step 1 — Open Terminal in the right folder (2 min)

Press **Cmd + Space**, type `Terminal`, hit Enter. Then paste this and press Enter:

```bash
cd ~/Documents/ttc-bus-delays
```

Check you're in the right place:

```bash
ls
```

You should see exactly four files: `LAUNCH.md`, `README.md`, `analyze.py`,
`index.html`, `requirements.txt`. If you see something else, you're in the wrong
folder — re-run the `cd` line.

---

## Step 2 — Install the two libraries (2 min)

```bash
pip3 install -r requirements.txt
```

**If that errors**, try in this order:

| Error message contains | Run this instead |
|---|---|
| `command not found: pip3` | `python3 -m pip install -r requirements.txt` |
| `externally-managed-environment` | `pip3 install --user -r requirements.txt` |
| `Permission denied` | `pip3 install --user -r requirements.txt` |

You only ever do this once.

---

## Step 3 — Prove the logic works before downloading anything (1 min)

```bash
python3 analyze.py --selftest
```

You should see a list of `ok` lines ending in **`all checks passed`**. This
downloads nothing — it just proves the cleaning code does what it claims. If
this fails, stop and send me the error; nothing after this will work.

---

## Step 4 — Run the real analysis (5–10 min)

Start with recent years so you see it work quickly:

```bash
python3 analyze.py --since 2023
```

It prints each file as it downloads, then finishes with your findings in plain
English — the top causes, the worst locations, the worst routes, the worst hour.

**Read that output.** It is the actual result of the project. Screenshot it or
copy it somewhere.

Once you've seen it work, get the full picture (about 15 minutes):

```bash
python3 analyze.py
```

That covers 2014 to now. It overwrites `data.json` with the bigger dataset.

> **If a file fails to download**, the script prints `SKIPPED` and carries on
> with the rest. That's fine — one missing year won't break anything.

---

## Step 5 — Look at it (2 min)

**Do not double-click `index.html`.** Chrome blocks pages opened as files from
reading `data.json`, so you'll get an empty page even though everything worked.

Instead, in the same Terminal window:

```bash
python3 -m http.server 8000
```

Then open **http://localhost:8000** in your browser. That's your dashboard.

Click through it: hover the bars, open a couple of "Show data table" panels,
try the dark mode button. When you're done, press **Ctrl + C** in Terminal to
stop the server.

---

## Step 6 — Write your finding (15 min — this is the important one)

Everything so far was mechanical. This step is the one that gets you hired.

Look at your own numbers and answer three questions in writing:

1. **What causes the most lost time, and is it what you expected?** Compare the
   hours column against the incident count — the biggest cause by time is often
   not the most frequent one.
2. **Which locations or routes stand out, and do you know why?** You live here.
   If Jane & Finch or a particular route tops the list, you probably have a
   theory. Say it.
3. **When is it worst?** Look at the hour chart. Is the evening peak worse than
   the morning? By how much?

Now write **two sentences** and put them at the top of the page. Open
`index.html` in TextEdit (right-click → Open With → TextEdit), find this line
near the top:

```html
  <div id="finding"></div>
```

Replace it with your own paragraph:

```html
  <div class="card" style="margin-bottom:4px">
    <p class="note" style="margin:0">
      <strong>What the data shows:</strong> YOUR FIRST SENTENCE.
      YOUR SECOND SENTENCE.
    </p>
  </div>
```

Save. Refresh `localhost:8000` to check it looks right.

**Why this matters more than the charts:** anyone can publish a dashboard. A
hiring manager skims it in six seconds. The sentence that says *here is what I
found and here is why it's surprising* is the thing they remember, and it's the
thing they'll ask you about in an interview.

---

## Step 7 — Put it on GitHub (10 min)

**7a. Make the repository.** Go to github.com → **+** (top right) → **New
repository**.

- Name: `ttc-bus-delays`
- **Public**
- **Don't tick** "Add a README", ".gitignore", or "license" — you already have them
- **Create repository**

**7b. Upload the files.** On the new empty repo page, click
**uploading an existing file**.

Open `Documents/ttc-bus-delays` in Finder, select **all five files**
(Cmd + A works), and drag them onto the upload area:

```
README.md   LAUNCH.md   analyze.py   index.html   data.json
```

Every file is visible — there are no hidden folders in this project, so
drag-and-drop just works. Type a commit message like
`TTC bus delay analysis` and click **Commit changes**.

> `data.json` is the one people forget. Without it the published page will be
> empty. Check it's in the list before you commit.

**7c. Turn on the website.** In your repo: **Settings** → left sidebar
**Pages** → under "Build and deployment":

- **Source:** `Deploy from a branch`
- **Branch:** `main`, folder: **`/ (root)`**
- **Save**

Wait a minute or two, then reload that Settings → Pages screen. Your URL appears
at the top:

```
https://<your-username>.github.io/ttc-bus-delays/
```

**7d. Check it.** Open the URL. You should see your numbers, your finding, and
working charts. If the page loads but the charts are empty, `data.json` didn't
get uploaded — go back to 7b.

---

## Step 8 — Make it count (20 min)

The project only helps if people see it.

**Resume.** Replace the TTC Pulse entry with this, filling in your real numbers:

> **TTC Bus Delays — Toronto Transit Analysis** | *Python, pandas* | `<your-url>`
> - Cleaned and analyzed N bus delay records published by the City of Toronto to
>   identify what causes the most lost service time, where, and when.
> - Matched inconsistently typed location names (`JANE AND FINCH`, `Jane & Finch`,
>   `FINCH AVE AT JANE ST`) into single entries, without which the busiest
>   intersections split across spellings and never surface in a ranking.
> - Found YOUR FINDING HERE.
> - Published the results as a public dashboard with hover detail, data tables
>   and dark mode.

**LinkedIn headline:**

> Data & Business Analyst | Published TTC delay analysis (Python, SQL, Power BI) | Seneca Data Science grad

**LinkedIn Featured section** (Profile → Add section → Recommended → Add
featured → Add a link): paste your URL. It shows as a clickable card near the
top of your profile.

**Outreach message** — ten a week to Seneca alumni and junior analysts at Toronto
companies:

> Hi [Name] — I'm a Seneca data science grad in Toronto. I analysed the City's
> TTC bus delay data to work out what actually causes the most lost service time:
> [your-url]
>
> I saw you work as an analyst at [Company] — would you be open to a 15-minute
> call about what your team uses day to day? Trying to spend my time on the right
> things.

Don't ask for a referral in the first message.

---

## If something breaks

Copy the **exact** error text and send it. Nothing here is dangerous — the script
only reads public data and writes one file in its own folder, so a failed run
costs you nothing but a re-run.

## Re-running later

The City publishes new data monthly. To refresh:

```bash
cd ~/Documents/ttc-bus-delays
python3 analyze.py
```

Then upload the new `data.json` to GitHub (**Add file → Upload files**, drag it
in — uploading a file that already exists just replaces it).
