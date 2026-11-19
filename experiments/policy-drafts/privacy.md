# Privacy Policy

> **Draft, not legal advice.** Written for Ekido ticket A4 against India's Digital Personal Data Protection Act, 2023 (DPDP Act) basics, and reviewed by Piyush. A lawyer must review it before launch. Items marked **[TO CONFIRM]** are decisions or facts the company has not settled yet (for example the legal entity, which does not exist yet, and the contact details).

*Version: draft 1 · Last updated: 19 November 2026*

This page explains what personal data Ekido collects, why, how long we keep it and what you can ask us to do with it. Ekido is currently in a **test period using test money only**; where that changes what happens, we say so.

## 1. Who we are

Ekido is run by **[legal entity name and registered address: TO CONFIRM. The company is not registered yet]**. In this policy "we" and "Ekido" mean that entity. For the DPDP Act we are the *data fiduciary* for the personal data of people who sign up. When you upload data that contains other people's personal details, you decide why and how it is used, and we act for you as a *data processor*.

## 2. What we collect and why

| Data | Why we need it | When we ask for it |
|---|---|---|
| **Email address**, and your name if you give it | To sign you in (by email link or Google), to run your team, and to send you receipts and service messages | When you sign up |
| **Google account basics** (name, email) if you use Google sign-in | The same | When you choose Google sign-in |
| **Team and role details**, **API keys** (we store only a one-way fingerprint, never the key itself) | To control who can do what | When you create a team or a key |
| **Training examples and test examples** you upload (a CSV or similar) | To train, check and run your model. This is the purpose; we use them for nothing else | When you upload |
| **Your instructions to the assistant** | To set up the job and show you a price and quality terms | When you use the assistant |
| **Your models, results and checkpoints** | To give you your model, endpoint and download | While a job runs and after |
| **Requests sent to your hosted model**, and counts of them | To run the endpoint and to meter usage and plan limits. We do **not** keep the text of requests in our logs | When your endpoint is used |
| **Payment details**: the amount, the order and the payment status, and GST invoice details such as a business name, address and GSTIN | To charge you, refund you and issue GST invoices. **Card and UPI details are handled by our payment company, Razorpay, and we do not store them** | When you pay |
| **Technical data**: IP address, browser type, error logs and a request ID | To keep the service secure and to find faults | Automatically |
| **Consent records**: what you agreed to, and when | To prove consent, as the DPDP Act requires | When you agree |

We do not sell personal data. We do not use your uploaded data to train models for anyone else. We do not use advertising trackers **[TO CONFIRM against what the website actually loads]**.

## 3. Consent

We ask for your consent in plain words before we collect personal data, and we say what it is for. You can withdraw consent at any time (see section 7); withdrawing may mean we can no longer provide the service. Some processing we do because the law requires it (for example, keeping tax records) and not because of consent.

## 4. Your uploaded data, and the limits you should know about

- **Removal of personal details in your browser.** Before anything is uploaded, your browser removes common personal details (names, phone numbers, emails, Aadhaar, PAN, GSTIN, UPI IDs and addresses) from your examples. This is automatic and **not perfect**; it can miss things and can remove things it should not. Check the preview before you upload.
- **Encryption.** Your data is encrypted in your browser before it leaves, and stays encrypted in our storage. Each job has its own key. Only the devices working on your job receive that key, only while they work on it. When you delete your data, we destroy the key so that every copy, including backups, can no longer be read.
- **The honest limit.** The device that trains your model has to read your data while it trains. Encryption protects your data on its way and in storage; it does not hide it from the device doing the work. If your data is sensitive, tell us before you use Ekido: we plan to offer private pools (your own machines only) and verified providers. **[TO CONFIRM what is available at launch]**
- **Who is connected stays private.** We do not tell you which device handled your job, and we do not tell the device who you are.

## 5. How long we keep data

| Data | Kept for |
|---|---|
| Uploaded datasets | Until you delete them, or 90 days after the last job that used them, whichever is first |
| Trained models | While your account is active; a finished model is kept for 90 days after a job ends if you have not asked for it to be kept longer **[TO CONFIRM the exact rule]** |
| Checkpoints | Until the job ends, then in a 30-day holding area before they are destroyed |
| Account data | While your account is active, and then **[TO CONFIRM]** |
| Payment and invoice records | As long as tax and accounting law require **[TO CONFIRM: usually several years]** |
| Technical logs | **[TO CONFIRM, for example 30 to 90 days]** |
| Anything you ask us to delete | Within **30 days** of your request (see section 7) |

## 6. Who else sees your data

We use a few providers to run Ekido. They act on our instructions:
- **Amazon Web Services**, Mumbai region: servers, storage, email sending and key management.
- **Razorpay**: taking payments and refunds.
- **Google**: sign-in, only if you choose it.
- **Devices on the Ekido network** that train or check your model, as described in section 4.

We may also share data when the law requires it, or to protect people from serious harm. Your data is stored in India. If any of it is transferred outside India in future, we will tell you and follow the DPDP Act's rules. **[TO CONFIRM]**

A record of each paid job (a fingerprint of its terms, its quality result and its payout split, **never your data or your name**) is written to a public blockchain test network so that anyone can check it was not changed. A fingerprint cannot be turned back into the original, and public records cannot be deleted.

## 7. Your rights

Under the DPDP Act you can:
- **Access**: ask for a summary of the personal data we hold and how it is used. You can export your data from your account (**Export my data**).
- **Correct** data that is wrong or out of date.
- **Erase** your data: use **Delete my data** in your account, or write to us. We will do it within 30 days, and we will record that it was done.
- **Withdraw consent** at any time.
- **Get your grievance handled** (section 8).
- **Nominate** another person to exercise these rights for you if you die or become unable to.

We may keep what the law requires us to keep, such as invoices, and will tell you if so.

## 8. Grievance officer and complaints

Write to our grievance officer: **[name, email and postal address: TO CONFIRM before launch]**. We will reply within **[TO CONFIRM; the law sets the outer limit]**. If you are not satisfied, you can complain to the Data Protection Board of India once it is operating.

## 9. Children

Ekido is for businesses and adults. You must be **18 or older** to create an account **[TO CONFIRM: the DPDP Act treats anyone under 18 as a child]**. We do not knowingly collect personal data from anyone under 18 and we do not track or target children. If you believe a child has given us data, write to the grievance officer and we will delete it. If you upload data that contains children's personal data, you are responsible for having the consent the law requires.

## 10. Security and breaches

We encrypt data in storage and in transit, store only fingerprints of sign-in links, sessions and API keys, limit who can read what, and keep an audit log of admin actions. No system is perfectly secure. If a breach affects your personal data we will tell you and the Data Protection Board as the law requires.

## 11. Changes

We will show the date of the latest version at the top, and tell account owners by email about significant changes.
