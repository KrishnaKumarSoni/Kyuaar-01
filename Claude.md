CLAUDE CODE: Kyuaar.com Project Guidelines
Product Overview
Kyuaar.com is a platform for pre-printed QR code packets that enable dynamic redirections, primarily for businesses to connect customers to WhatsApp or custom URLs. Each packet contains a configurable number of identical QR codes (default 25) that all point to a unique base URL. On first scan (after setup and sale), users configure a redirect (e.g., by entering a phone number), which applies to the entire packet. QR codes are generated externally via third-party tools (e.g., QRCode Monkey or GoQR.me for custom styles like rounded corners, burnt orange theme) and uploaded as images to the platform. The platform handles base URL generation, QR image uploads, packet states (setup pending/done, configuration pending/done), dynamic redirections, and basic business tracking for sales and revenue.
Key Features

* Packet Creation: Generate packets with unique IDs and base URLs (e.g., kyuaar.com/packet/[id]). Specify the number of QRs in the packet (1-100). No QR images are generated in-app; only the endpoint is created. Initial state: Setup Pending.
* QR Upload and Management: After packet creation, admins can select a packet in the dashboard and upload QR images (PNG/JPG) generated externally encoding the base URL. Support uploading one image (representing identical QRs). Update state to Setup Done on successful upload.
* Packet States:

Setup Pending: Packet created but no QR image uploaded.
Setup Done: QR image uploaded and ready for distribution/sale.
Configuration Pending: Packet marked as sold (offline), ready for customer configuration via first scan.
Configuration Done: Customer has scanned and set the redirect (e.g., WhatsApp number or custom URL).


* Configuration Journey:

Scans to base URL check packet state:

If Setup Pending: Show error page ("Packet not ready").
If Setup Done but Configuration Pending: On first scan, show config page on customer's mobile to enter/validate phone number (e.g., +919166900151) or custom URL. Set redirect in DB to wa.me/[number] or custom URL, then update state to Configuration Done.
If Configuration Done: Redirect to the set URL for all subsequent scans.




* Customer Lifecycle Flows:

Offline Sale: Admin marks packet as sold in dashboard (e.g., via button), enters buyer details (name, email, price paid). State changes to Configuration Pending. Optionally print/ship packet with instructions to scan for setup.
Post-Sale: Customer receives packet, scans QR (opens config page on mobile), sets redirect. System logs this and updates to Configuration Done.
Updates: Customers can re-scan to edit redirect if needed (admin-configurable).


* User Journey (Customer's Voice): "Bought 25 QR stickers from Kyuaar offline. Admin marked it sold, I generated QRs externally with the base URL, uploaded. Scanned one to set my WhatsApp on my phone – simple form. Now, customers scan from my shop and chat instantly. Dashboard shows it's all configured!"
* Business Model: Sell packets offline. Track sales, pricing, and revenue in admin dashboard for simple business operations.

Tech Stack Requirements

* Backend: Python Flask for API, routing, DB management.
* Frontend: HTML, CSS, JS. Use shadcn/ui core components ONLY (integrate via CDN like unpkg.com/shadcn-ui for buttons, cards, selects, tables – no custom hardcoded components). Use Phosphor icons where required. Do not hardcode design CSS manually ever; always use off-the-shelf shadcn/ui components and their built-in theming options.
* Database: Firebase Firestore. Store packet data including unique ID, base URL, QR count, uploaded image URLs (in Firebase Storage), redirect config, states (setup/config), sale details (buyer name, price, date sold), and scan logs.
* Image Handling: Use Firebase Storage for uploading and serving QR images. No in-app QR generation; handle file uploads via Flask forms and Firebase SDK.
* Deployment: Vercel (serverless Flask). GitHub repo: Kyuaar-01, pushed via CLI.
* Theme: Dark mode by default, with burnt orange primary accents (#CC5500) via CSS variables and shadcn/ui theming (e.g., set primary color in shadcn config and apply dark mode classes).
* Other: Flask-Login for admin auth, gunicorn for serving.

No React – keep it simple Flask templates with shadcn CSS/JS.
Admin Panel Requirements
Secure dashboard at /admin (login-protected) for business operations. Use shadcn components for UI (e.g., tables for lists, cards for stats, forms for inputs).

* Authentication: Username/password login (Flask-Login).
* Dashboard Overview: Stats cards showing total packets created, sold, revenue earned, packets by state (e.g., counts of Setup Pending, Configuration Done), recent sales, scan counts.
* Packet Management:

Create: Form for QR count (1-100), optional pricing (set base price per packet or per QR). Auto-generate unique ID and base URL. Set initial state: Setup Pending. Optionally mark as sold immediately (for quick offline sales).
Upload QR: Select packet from list, upload image. Validate (e.g., file type, size < 5MB). Update to Setup Done. Show preview in dashboard.
Mark as Sold: For Setup Done packets, button/form to mark sold: Enter buyer name/email, sale price (default from creation or editable), date. Update state to Configuration Pending. Log for revenue tracking.
List/Edit: Table of packets with columns: ID, Base URL, QR Count, State (Setup Pending/Done, Config Pending/Done), Sale Price, Buyer, Redirect URL, Uploaded Image Preview. Actions: Edit details, reset states/redirects, delete.


* Sales and Pricing Configurations:

Simple Pricing: During packet creation or marking sold, input fields for price per packet (e.g., default $10 for 25 QRs). Auto-calculate based on QR count if needed (e.g., $0.40 per QR).
Revenue Tracking: Dashboard section with total revenue, sales history table (packet ID, buyer, price, date), basic charts (use simple JS like Chart.js via CDN for monthly earnings).
Minimal Business Flows:

Offline Sale Flow: Create packet → Upload QR → Mark as Sold (enter details) → Email buyer instructions (auto-generate with base URL for their reference, even though QR is pre-uploaded).
Fulfillment: Button to generate shipping label or email PDF instructions (no actual PDFs since QRs are external).
Refunds/Returns: Simple button to mark packet as returned, adjust revenue.




* User/Redirect Management:

View configs per packet (e.g., in a modal: current redirect, scan history).
Analytics: Log scans (count, timestamps, success rates). Filter by state (e.g., alert on Configuration Pending packets overdue).


* Settings: Theme tweaks, DB backups, error logs, default pricing settings (e.g., set global price per QR).
* Security: Rate limiting, input validation (e.g., validate prices as numbers, image uploads), HTTPS. Ensure state transitions are atomic (e.g., can't mark sold if Setup Pending).

Reliability for QR Handling and Flows
Since QR generation is external:

* Instruct users/admins to generate QRs encoding the base URL via third-party tools (e.g., QRCode Monkey for custom styles).
* Upload Handling: Use Flask to manage form uploads, integrate Firebase Storage SDK. Validate images client-side (JS) for QR validity if possible (e.g., using jsQR library via CDN).
* State Management: Use Firestore transactions for reliable updates (e.g., on upload: update state and store image URL atomically). On config set: Update from Pending to Done only after successful DB write.
* Business Flows Reliability: Log all state changes with timestamps/user IDs. Include alerts (e.g., email admin if a sold packet remains Config Pending > 7 days).
* Test: Unit tests for state transitions, upload flows, pricing calculations, redirection logic, and analytics queries.
* Performance: Handle uploads and state updates asynchronously (use threading for MVP).

Deployment Instructions
Prompt Claude to include a deploy.sh script:

* Create GitHub repo Kyuaar-01 via gh CLI (e.g., gh repo create Kyuaar-01 --public).
* Git add/commit/push (e.g., git add .; git commit -m "Initial commit"; git push origin main).
* Deploy to Vercel via vercel CLI (install via npm i -g vercel; then vercel --prod; configure as Python project in vercel.json with build command: pip install -r requirements.txt, and output directory: .).

For WSGI-based imports (detailed explanation): Vercel deploys Flask apps serverlessly, but Flask is a WSGI (Web Server Gateway Interface) application. WSGI is a Python standard (PEP 3333) for web servers to communicate with web apps. To make Flask Vercel-compatible:

* Use Gunicorn as the WSGI server (install via pip: gunicorn).
* Create a wsgi.py file with: from app import app; application = app (assuming your Flask app is in app.py).
* In vercel.json, set the runtime to Python and the entry point to gunicorn (e.g., "framework": "flask", but manually configure if needed).
* Start command: gunicorn -w 1 -k gthread --timeout 60 wsgi:application.
* This ensures Vercel's serverless functions wrap your Flask app via WSGI, handling requests efficiently without a persistent server. Test locally with gunicorn before deploying. If issues arise, fallback to a Procfile with web: gunicorn wsgi:application.
verceo project name: kyuaar-01 (create new)