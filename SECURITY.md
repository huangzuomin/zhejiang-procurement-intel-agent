# Security Policy

## Supported Versions

This project is currently pre-1.0. Security fixes are accepted on the default branch.

## Reporting a Vulnerability

Please open a private security advisory on GitHub if available, or contact the repository owner through GitHub with a minimal report.

Helpful details include:

- Affected file or command.
- Impact and reproduction steps.
- Whether public data, local runtime files, or credentials are involved.

## Data and Credential Boundaries

The project is designed for public Zhejiang government procurement notices. It must not require committed secrets.

Never commit:

- `.env` files.
- DingTalk webhooks or app secrets.
- Browser cookies, session storage, or login state.
- Private procurement documents.
- Runtime databases or generated reports unless explicitly approved as public fixtures.

The scraper must not bypass CAPTCHA, authenticate as a user, or submit forms.
