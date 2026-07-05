# GCP setup — one-time console work (Phase A)

The only part of the v2 migration that needs a human: creating the project and
wiring auth. Everything below is copy-paste; the Cloud Shell blocks run in the
console's built-in terminal (>_ icon, top right) so nothing needs installing
locally. Budget: this project lives comfortably inside the BigQuery free tier
(10 GB storage / 1 TB query per month — we use megabytes); the alerts exist to
catch surprises, not expected spend.

## 1. Project + billing (console)

1. https://console.cloud.google.com → create project, ID `fdic-monitor`
   (any free ID works — it just has to match `GCP_PROJECT` everywhere below).
2. Attach the billing account to the project.
3. Billing → Budgets & alerts → create a budget for this project:
   $25/month with alert thresholds at 40% ($10) and 100% ($25).

## 2. Enable APIs (Cloud Shell)

```sh
# iamcredentials is what WIF uses to mint the service account's token —
# without it every CI auth fails with SERVICE_DISABLED
gcloud services enable bigquery.googleapis.com bigquerystorage.googleapis.com \
  storage.googleapis.com sheets.googleapis.com drive.googleapis.com \
  iamcredentials.googleapis.com \
  --project fdic-monitor
```

## 3. Service account + Workload Identity Federation (Cloud Shell)

Keyless CI auth: GitHub Actions presents its OIDC token, GCP trusts it for
this one repo, no JSON key exists anywhere. Run as one block:

```sh
PROJECT=fdic-monitor
REPO=yugveerj/fdic-bank-health-monitor

gcloud iam service-accounts create fdic-ci \
  --project $PROJECT --display-name "CI ingestion + dbt"

gcloud projects add-iam-policy-binding $PROJECT \
  --member "serviceAccount:fdic-ci@$PROJECT.iam.gserviceaccount.com" \
  --role roles/bigquery.jobUser

gcloud projects add-iam-policy-binding $PROJECT \
  --member "serviceAccount:fdic-ci@$PROJECT.iam.gserviceaccount.com" \
  --role roles/bigquery.dataEditor

gcloud iam workload-identity-pools create github \
  --project $PROJECT --location global --display-name "GitHub Actions"

gcloud iam workload-identity-pools providers create-oidc github-actions \
  --project $PROJECT --location global --workload-identity-pool github \
  --display-name "GitHub Actions OIDC" \
  --issuer-uri "https://token.actions.githubusercontent.com" \
  --attribute-mapping "google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition "assertion.repository == '$REPO'"

PROJECT_NUMBER=$(gcloud projects describe $PROJECT --format 'value(projectNumber)')

gcloud iam service-accounts add-iam-policy-binding \
  fdic-ci@$PROJECT.iam.gserviceaccount.com \
  --project $PROJECT --role roles/iam.workloadIdentityUser \
  --member "principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github/attribute.repository/$REPO"

echo "GCP_WIF_PROVIDER=projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github/providers/github-actions"
```

(BigQuery Data Editor is project-wide for now — simplest while datasets are
still being created by CI. Storage Object Admin on the reports bucket comes
with Phase D, and the Google Sheet share with the Tableau path.)

## 4. GitHub repo variables (github.com → repo → Settings → Secrets and variables → Actions → Variables)

None of these are sensitive, so they're variables, not secrets:

| variable | value |
| --- | --- |
| `GCP_PROJECT` | `fdic-monitor` |
| `GCP_WIF_PROVIDER` | the `projects/…/providers/github-actions` line echoed above |
| `GCP_SA_EMAIL` | `fdic-ci@fdic-monitor.iam.gserviceaccount.com` |

The existing `FRED_API_KEY` and `MOTHERDUCK_TOKEN` secrets stay as they are —
the branch CI uses both (MotherDuck read-only, for the parity check) until
decommission.

Once the three variables exist, the `v2 BigQuery ingest` workflow stops
skipping its ingest job: the next push to `v2-bigquery` (or a manual
workflow_dispatch run) does the full ingest into `fdic_raw` and the raw
parity check against production. Fallback if WIF misbehaves: a JSON key for
`fdic-ci` in an Actions secret with `credentials_json` on the auth step —
recorded in decisions.md if we ever need it.

## 5. Archive bucket + storage role (Phase C decommission; also serves Phase D reports)

One private bucket for the final MotherDuck snapshot (cold storage) and the
Storage Object Admin role the spec assigns the service account anyway:

```sh
gcloud storage buckets create gs://fdic-monitor-archive --project fdic-monitor \
  --location US --uniform-bucket-level-access --public-access-prevention

gcloud projects add-iam-policy-binding fdic-monitor \
  --member "serviceAccount:fdic-ci@fdic-monitor.iam.gserviceaccount.com" \
  --role roles/storage.objectAdmin
```

Then add a repo variable `GCS_ARCHIVE_BUCKET` = `fdic-monitor-archive`.
(The public reports bucket is a separate Phase D decision — nothing public
is created here.)

## 6. Local dev (optional, for running ingestion from this machine)

```sh
# install the gcloud CLI (macOS): brew install --cask google-cloud-sdk
gcloud auth application-default login
```

Then set `GCP_PROJECT=fdic-monitor` in `.env` (see `.env.example`).
