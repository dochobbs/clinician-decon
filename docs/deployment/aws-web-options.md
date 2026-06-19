# AWS Web Deployment Options

Last reviewed: 2026-06-19.

## Recommendation

Use AWS first as a public trust/download site, not as the PHI-processing decon runtime.

The current product promise is local decontextualization: raw pasted clinical text stays on the
clinician's Mac and only the reviewed scrubbed draft is copied out. A conventional AWS-hosted web
app would change that boundary because source text would leave the user's device unless the model
runs entirely in the browser.

## Option 1: Static Trust And Download Site

What it does:

- Hosts a public web page explaining Decon, decon vs de-id, audit notes, and install steps.
- Hosts the DMG download.
- Does not accept pasted clinical text.
- Does not run the decon API in AWS.

Suggested AWS shape:

- S3 bucket for static assets and DMG storage.
- CloudFront distribution in front of S3.
- Optional Route 53 domain.
- Optional AWS WAF if traffic patterns justify it.

Rough cost:

- S3 storage for a 1.7 GB DMG is cents per month.
- CloudFront has a free plan that currently includes 100 GB data transfer out per month.
- If free-plan limits do not apply, DMG download bandwidth dominates cost.
- At 1.7 GB per DMG, 100 downloads is about 170 GB served.
- At a public transfer price around $0.085/GB in common US tiers, 100 downloads would be about
  $14-$15 in transfer before taxes and request costs.
- A low-traffic trust page without many DMG downloads should usually be under $5/month.

Good for:

- Sharing the installer.
- Letting clinicians and IT/security reviewers inspect the package audit.
- Keeping the actual PHI path local.

## Option 2: Browser-Only Local Decon

What it does:

- Hosts a static web app.
- Downloads the model or a browser-compatible derivative to the user's browser.
- Runs decon locally in the browser, without sending source text to AWS.

Suggested AWS shape:

- S3 plus CloudFront, or Amplify Hosting.
- No decon API endpoint.
- Strong Content Security Policy.
- Explicit offline/cache behavior after first load.

Rough cost:

- Similar to Option 1, but model download bandwidth may exceed DMG bandwidth.
- Amplify Hosting lists static data served outside free tier at $0.15/GB.
- CloudFront/S3 may be cheaper for high download volume, depending on free-plan eligibility and
  regional traffic.

Risks and work:

- The current OpenMed Python/transformers runtime is not browser-native.
- A browser build would likely require ONNX/WebGPU/WASM packaging and separate validation.
- First-run latency may be materially worse because the model downloads through the browser.
- This is a future product path, not a quick deploy of the current Mac app.

## Option 3: Hosted Decon API

What it does:

- Runs the decon API in AWS.
- Browser sends source clinical text to AWS for processing.

Suggested AWS shape:

- ECS Fargate service or EC2 instance running the local server behind an Application Load Balancer.
- Private networking, TLS, authentication, audit controls, retention policy, and log redaction.
- BAA-covered AWS account and explicit HIPAA control review before any real PHI use.

Rough cost:

- A small always-on Fargate service sized around 2 vCPU and 8 GB memory is roughly $65-$75/month
  before load balancer, logs, NAT, storage, monitoring, and traffic.
- An Application Load Balancer commonly adds about $16-$25/month before usage-based LCU charges.
- Practical pilot cost is likely $90-$150/month for a minimal always-on hosted API.
- Larger model/runtime requirements, higher availability, or GPU needs increase cost quickly.

Recommendation:

- Do not ship this as the default product path.
- Only use this path for a BAA-covered, authenticated, explicitly logged pilot where users know raw
  source text is leaving the device.

## Near-Term Deployment Plan

1. Build the self-contained Mac DMG.
2. Publish a static trust/download site on S3 plus CloudFront.
3. Include:
   - product overview
   - decon vs de-id explainer
   - package audit
   - install steps
   - model/source attribution
   - checksum for the DMG
4. Keep the app's runtime local.
5. Evaluate browser-only decon separately as a research spike.

## Pricing Sources To Recheck Before Launch

- S3 pricing: https://aws.amazon.com/s3/pricing/
- CloudFront pricing: https://aws.amazon.com/cloudfront/pricing/
- Amplify pricing: https://aws.amazon.com/amplify/pricing/
- Fargate pricing: https://aws.amazon.com/fargate/pricing/
- Elastic Load Balancing pricing: https://aws.amazon.com/elasticloadbalancing/pricing/
