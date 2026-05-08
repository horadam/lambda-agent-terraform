# Lambda Agent on AWS — Project Spec

A learning project to refresh AWS and pick up Terraform + GitHub Actions, built around deploying a small AI agent as an AWS Lambda function. Designed for interview preparation — every milestone calls out the concepts you should be able to discuss.

---

## Goal

Build a GitHub repository containing:
- A simple **AI agent** (Python) that runs as an **AWS Lambda function**
- **Terraform** code that provisions all AWS resources (Lambda, IAM, Secrets Manager, CloudWatch logs, Function URL)
- A **GitHub Actions** pipeline that deploys both infrastructure and code on push to `main`
- **OIDC trust** between GitHub and AWS (no long-lived AWS keys stored in GitHub)

End state: push to `main` → GitHub Actions assumes an AWS role → Terraform applies → Lambda is updated → you can `curl` the Function URL and get a response from your agent.

---

## Non-goals (keep scope small)

- No frontend, no database, no API Gateway with custom domain — a Lambda Function URL is enough
- No multi-environment setup (no `dev`/`staging`/`prod` workspaces) — single environment
- No remote Terraform state at first — start with local state, add S3 backend as a stretch goal
- No fancy agent — one LLM call with one tool is plenty

---

## Tech choices

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.12 | First-class Lambda runtime, simplest agent code |
| Agent SDK | `anthropic` Python SDK | You already know the API; minimal deps |
| IaC | Terraform (latest, ~1.9+) | Industry standard, the thing to learn |
| CI/CD | GitHub Actions | Same |
| AWS auth from CI | OIDC + IAM role | Modern best practice, common interview topic |
| Secret storage | AWS Secrets Manager | The thing the friend specifically suggested |
| Lambda invocation | Lambda Function URL | Simpler than API Gateway, free, HTTPS out of the box |
| Lambda packaging | Zip via Terraform `archive_file` | Simplest; revisit container images later |

---

## Repository layout

```
lambda-agent/
├── README.md                    # what this is, how to deploy, how to invoke
├── SPEC.md                      # this file
├── .gitignore                   # standard Terraform + Python ignores
│
├── agent/                       # Lambda function source
│   ├── handler.py               # Lambda entrypoint
│   ├── agent.py                 # the agent loop (LLM call + tool)
│   ├── requirements.txt         # anthropic, boto3 (boto3 is in runtime, but pin)
│   └── tests/
│       └── test_agent.py        # local unit tests, mocked LLM
│
├── terraform/                   # all infrastructure
│   ├── main.tf                  # provider, locals, top-level wiring
│   ├── variables.tf             # inputs (region, project name, etc.)
│   ├── outputs.tf               # function URL, role ARNs
│   ├── lambda.tf                # Lambda function, log group, packaging
│   ├── iam.tf                   # Lambda execution role + policies
│   ├── secrets.tf               # Secrets Manager secret for ANTHROPIC_API_KEY
│   ├── github_oidc.tf           # OIDC provider + role GitHub Actions assumes
│   └── versions.tf              # required_providers, required_version
│
└── .github/
    └── workflows/
        ├── plan.yml             # runs `terraform plan` on PRs
        └── deploy.yml           # runs `terraform apply` on push to main
```

---

## Milestones

Each milestone is small enough to finish in one sitting and ends in a state you can demo and explain.

### Milestone 1 — Local Lambda function + agent code (no AWS yet)

Build the agent code and make sure it runs locally before touching infrastructure.

**Tasks:**
1. Create `agent/agent.py` — a function `run_agent(user_input: str) -> str` that:
   - Reads `ANTHROPIC_API_KEY` from environment
   - Makes one Claude API call with one tool defined (e.g., `get_current_time` — trivial Python function, no network needed)
   - Handles the tool-use loop: if the model calls the tool, run it, send the result back, return final text
2. Create `agent/handler.py` — the Lambda entrypoint `handler(event, context)`:
   - Parses input from a Function URL event (`event["body"]` is a JSON string with `{"input": "..."}`)
   - Calls `run_agent`
   - Returns `{"statusCode": 200, "body": json.dumps({"output": ...})}`
3. Write a tiny test script that calls `handler` with a fake event so you can run it locally with `python -m agent.handler`.
4. Pin deps in `agent/requirements.txt`.

**Concepts to understand:**
- **Lambda handler signature** — `(event, context)`, what's in each, why it's structured this way
- **Function URL event shape** — different from API Gateway events; know the difference
- **Cold start vs warm start** — module-level code runs once per container; put the Anthropic client there, not inside the handler, to reuse across invocations
- **The agent loop** — why it's a loop (model can call tools multiple times), what `stop_reason` values mean

**Done when:** You can run `ANTHROPIC_API_KEY=... python -c "from agent.handler import handler; print(handler({'body': '{\"input\": \"what time is it?\"}'}, None))"` and get a sensible answer back.

---

### Milestone 2 — Terraform: deploy the Lambda manually from your laptop

Get infrastructure-as-code working before adding CI/CD on top.

**Tasks:**
1. Install Terraform locally. Run `aws configure` with a personal IAM user that has admin (or scoped) permissions — this is just for bootstrapping; CI will use OIDC later.
2. Write `terraform/versions.tf` — pin Terraform version and AWS provider version.
3. Write `terraform/variables.tf` — `aws_region`, `project_name` (used as a prefix for all resource names).
4. Write `terraform/main.tf` — AWS provider block, `locals` for common tags.
5. Write `terraform/iam.tf` — Lambda execution role with the AWS-managed `AWSLambdaBasicExecutionRole` policy (gives CloudWatch Logs access).
6. Write `terraform/lambda.tf`:
   - Use `data "archive_file"` to zip `agent/` into `agent.zip`
   - `aws_lambda_function` resource pointing at the zip, runtime `python3.12`, handler `handler.handler`
   - Explicit `aws_cloudwatch_log_group` for the function (otherwise Lambda creates one with no retention — set `retention_in_days = 14`)
   - `aws_lambda_function_url` with `authorization_type = "NONE"` for now (we'll discuss auth later)
7. Write `terraform/outputs.tf` — output the function URL.
8. From `terraform/`: `terraform init`, `terraform plan`, `terraform apply`.
9. `curl -X POST <function_url> -d '{"input":"hi"}'` — but it'll fail because there's no API key yet. That's expected — next milestone.

**Concepts to understand:**
- **Terraform state** — what's in `terraform.tfstate`, why you don't commit it, why teams use remote backends (S3 + DynamoDB lock)
- **Providers vs resources vs data sources** — provider = plugin (AWS), resource = thing TF creates, data source = thing TF reads
- **`plan` vs `apply`** — plan is a dry run; apply executes; the plan output is the diff between desired (`.tf` files) and actual (state)
- **Implicit vs explicit dependencies** — Terraform builds a DAG from references (`aws_iam_role.lambda.arn`); explicit `depends_on` only when there's a hidden dependency
- **IAM trust policy vs permissions policy** — trust = "who can assume this role", permissions = "what can this role do"; Lambda's execution role is trusted by `lambda.amazonaws.com`

**Done when:** Terraform deploys the Lambda and prints a Function URL. You can hit it with curl and see a 5xx error from the Lambda (because no API key yet) in CloudWatch logs.

---

### Milestone 3 — Secrets Manager + Lambda fetches the secret at runtime

Wire up the Anthropic API key properly. Don't put it in a Terraform variable that goes into Lambda env vars in plain text — use Secrets Manager.

**Tasks:**
1. Write `terraform/secrets.tf`:
   - `aws_secretsmanager_secret` named `${var.project_name}/anthropic-api-key`
   - `aws_secretsmanager_secret_version` — but **don't** put the actual key in Terraform. Instead, create the secret with a placeholder value, then put the real key in via the AWS console or CLI once. Add a `lifecycle { ignore_changes = [secret_string] }` so Terraform doesn't overwrite it on subsequent applies.
2. Update `terraform/iam.tf` — add a custom policy to the Lambda role granting `secretsmanager:GetSecretValue` on that specific secret ARN (least privilege — not `*`).
3. Update `terraform/lambda.tf` — pass the secret's name (not value) as an env var: `SECRET_NAME = aws_secretsmanager_secret.anthropic.name`.
4. Update `agent/handler.py` (or a new `agent/secrets.py`):
   - At module load, use `boto3` to fetch the secret and set `ANTHROPIC_API_KEY` in `os.environ`
   - Cache it (module-level) so warm invocations don't re-fetch
5. `terraform apply`, then `aws secretsmanager put-secret-value` with the real key, then re-test the curl.

**Concepts to understand:**
- **Why Secrets Manager over Lambda env vars** — env vars are visible to anyone with `lambda:GetFunctionConfiguration`; Secrets Manager has separate IAM, audit logs, rotation support
- **Why `ignore_changes` on the secret value** — separates "the secret exists" (Terraform's job) from "the secret's value" (operator's job); avoids putting plaintext in state
- **IAM least privilege** — scope `Resource` to the specific secret ARN, not `*`
- **`boto3` in Lambda** — already installed in the runtime, no need to package; use it freely

**Done when:** `curl <function_url> -d '{"input":"what time is it?"}'` returns a real answer from the agent.

---

### Milestone 4 — GitHub Actions deploys via OIDC (the headline feature)

This is the most interview-relevant milestone. The pattern: GitHub Actions presents a signed OIDC token to AWS STS, AWS verifies it against a trust policy, and gives back temporary credentials. No static AWS keys in GitHub Secrets.

**Tasks:**
1. Push your repo to GitHub (private is fine).
2. Write `terraform/github_oidc.tf`:
   - `aws_iam_openid_connect_provider` for `https://token.actions.githubusercontent.com` (thumbprint can be hardcoded; it's well-known)
   - `aws_iam_role` named `${var.project_name}-github-actions` with a trust policy that:
     - Trusts the OIDC provider
     - Has a `Condition` on `token.actions.githubusercontent.com:sub` matching `repo:<your-gh-username>/<repo-name>:ref:refs/heads/main` (and optionally PR refs for the plan workflow)
     - Has a `Condition` on `aud` = `sts.amazonaws.com`
   - Attach a policy to that role granting whatever Terraform needs to manage these resources (Lambda, IAM, Secrets Manager, Logs, OIDC provider itself). For learning, you can start broad and tighten later.
3. `terraform apply` from your laptop one more time to create the OIDC role.
4. Write `.github/workflows/deploy.yml`:
   ```yaml
   on:
     push:
       branches: [main]
   permissions:
     id-token: write    # CRITICAL — lets the runner request an OIDC token
     contents: read
   jobs:
     deploy:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: aws-actions/configure-aws-credentials@v4
           with:
             role-to-assume: arn:aws:iam::<acct>:role/<project>-github-actions
             aws-region: us-east-1
         - uses: hashicorp/setup-terraform@v3
         - run: terraform init
           working-directory: terraform
         - run: terraform apply -auto-approve
           working-directory: terraform
   ```
5. Write `.github/workflows/plan.yml` — same shape, but on `pull_request`, runs `terraform plan` and posts the output as a PR comment (use `dflook/terraform-plan` action or roll your own).
6. Push a small change (e.g., tweak the agent's system prompt). Watch the Actions tab. It should deploy.

**Concepts to understand (most important section for interviews):**
- **OIDC vs static credentials** — long-lived `AKIA...` keys in GitHub Secrets are a leak risk; OIDC mints short-lived (1hr) creds per workflow run, scoped via trust policy
- **The trust policy `sub` condition** — this is the actual security boundary. `repo:org/repo:ref:refs/heads/main` means "only workflows running on the main branch of this specific repo." Without this condition, *any* GitHub workflow on the public internet could assume your role.
- **`permissions: id-token: write`** — without this, the runner can't request an OIDC token. Common gotcha.
- **`aud` claim** — extra sanity check that the token was minted for AWS specifically
- **Why not just use access keys** — be ready to articulate this clearly. "Static creds rotate poorly, leak through logs, and grant the same access whether the workflow is doing a `plan` or an `apply`. OIDC ties the credential to a specific workflow run on a specific branch."

**Done when:** Pushing to `main` triggers an Actions run that ends in a green checkmark and a deployed Lambda. You can show the Actions log proving no AWS keys are stored anywhere — only an IAM role ARN.

---

### Milestone 5 (stretch) — Polish

Pick any of these as time allows:

- **Remote Terraform state**: S3 bucket + DynamoDB lock table. Bootstrap problem: the bucket and table themselves need to exist before TF can use them as a backend. Solutions: a one-time bootstrap module, or use Terraform Cloud's free tier.
- **Tighten the OIDC role's permissions**: replace any broad policies with the minimum set needed. Good interview talking point.
- **Add a `terraform fmt` and `tflint` check** to the plan workflow.
- **Add basic observability**: a CloudWatch alarm on Lambda errors, a metric filter on the log group.
- **Function URL auth**: switch from `NONE` to `AWS_IAM` and call it with SigV4 — adds a layer to demo.
- **Container image deploy**: rebuild the Lambda as a container image pushed to ECR. Different packaging, different IAM, common in real codebases.

---

## Things to be careful about

- **Don't commit `terraform.tfstate`** — `.gitignore` it. State contains the secret ARN and other sensitive info.
- **Don't put the Anthropic API key anywhere in Terraform**, including not as a `variable` with a default. Use the placeholder + `ignore_changes` pattern.
- **Region consistency** — set `aws_region` once and reference it everywhere. Mixing regions causes weird errors.
- **The OIDC `sub` condition string format is finicky** — `repo:OWNER/REPO:ref:refs/heads/BRANCH` exactly. Copy-paste mistakes here cause "AccessDenied: Not authorized to perform sts:AssumeRoleWithWebIdentity" with no helpful detail.
- **Lambda timeout** — default is 3 seconds; an LLM call needs more. Set `timeout = 30` on the function.
- **Lambda memory** — default 128MB is fine for this; bumping memory also bumps CPU which can speed up cold starts if it matters.
- **CloudWatch log retention** — without an explicit `aws_cloudwatch_log_group`, Lambda creates one with infinite retention. Always set retention.

---

## How to use this spec with Claude Code

1. Create the empty repo, drop this `SPEC.md` in it, commit, push.
2. Open Claude Code in the repo.
3. Tell it: *"Read SPEC.md. We're going to do this milestone by milestone. Start with Milestone 1. Don't move on until I say so."*
4. After each milestone, ask Claude Code to **walk you through what it generated** — every resource, every parameter, what would happen if you removed it. This is the part that builds the interview-ready understanding. The "Concepts to understand" list at the end of each milestone is the checklist.
5. Resist the urge to let it do all five milestones in one shot. The point is the learning, not the deploy.