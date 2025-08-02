CLAUDE CODE: Kyuaar.com Project Guidelines

## Product Overview
Kyuaar.com is a revolutionary platform that empowers gig workers, service providers, and small businesses to build direct customer relationships and bypass platform commissions. Through pre-printed QR code packets, users create instant WhatsApp connections with customers, eliminating dependency on platforms like Uber, Zomato, Urban Company that take 20-30% commissions.

**The Core Revolution:** Transform one-time platform transactions into direct, recurring customer relationships via WhatsApp Business.

Each packet contains configurable QR codes (1-100) that point to a unique base URL. Users scan to configure their WhatsApp number or custom URL, instantly converting all QRs in the packet to direct customer connection points. This enables commission-free business growth and customer ownership.

## Target Customer Segments

### 1. Gig Economy Workers (Primary Market)
**Revenue Impact:** Keep 100% earnings instead of 70-80% after platform commissions
- **Cab/Auto Drivers:** Direct bookings for airport trips, office commutes, weekend trips
- **Food Delivery Partners:** Direct restaurant orders, skip Zomato/Swiggy commissions
- **Freelance Service Providers:** Direct client relationships without platform fees

### 2. Service Professionals (High Value Market)
**Revenue Impact:** Skip 30% Urban Company/platform commissions
- **Home Services:** Electricians, plumbers, AC repair, appliance technicians
- **Personal Care:** Salon professionals, massage therapists, beauticians
- **Health & Wellness:** Doctors, physiotherapists, dietitians, fitness trainers

### 3. Small Business Owners (Volume Market)
**Revenue Impact:** Build customer database, reduce marketing costs
- **Restaurants:** Direct table bookings, takeaway orders
- **Retail Shops:** Customer notifications, loyalty programs
- **Street Vendors:** Pre-orders, subscription services

### 4. Professional Services (Premium Market)
**Revenue Impact:** Higher-value recurring relationships
- **Consultants:** Lawyers, CAs, business advisors
- **Creative Professionals:** Photographers, designers, tutors
- **Real Estate & Insurance:** Direct lead generation

## Value Propositions by Segment

### Economic Empowerment
- **Commission Bypass:** Keep 100% of earnings vs 70-80% on platforms
- **Revenue Multiplication:** One QR packet → 50+ direct customers → ₹15,000+ extra monthly
- **Customer Ownership:** Build personal brand and recurring business
- **Platform Independence:** Reduce dependency on monopolistic platforms

### Customer Relationship Building
- **Direct WhatsApp Connection:** Personal relationship vs platform transaction
- **Recurring Revenue:** Regular customers book directly
- **Upselling Opportunities:** WhatsApp Business features (catalog, payments, broadcasts)
- **Community Building:** Customer groups, loyalty programs

### Operational Benefits
- **Instant Setup:** 30-second configuration via mobile
- **Offline Operation:** Works without internet (scan and save contact)
- **Professional Image:** Clean, branded QR codes vs handwritten numbers
- **Multilingual Support:** WhatsApp auto-translation for diverse customers
- **No Reprints Needed:** Master QR allows unlimited updates without reprinting
- **Lifetime Flexibility:** Change WhatsApp numbers, business info, seasonal offers anytime

## Revenue Generation Use Cases

### Immediate Revenue Impact
1. **Cab Driver Example:**
   - Investment: ₹33 for QR packet
   - Action: Leave QR sticker in car after every ride
   - Result: 2% passengers (1 per 50 rides) scan and save contact
   - Outcome: 1 direct booking/day × ₹500 = ₹15,000/month extra income
   - **ROI: 45,000%+ annually**

2. **Service Provider Example:**
   - Investment: ₹33 for QR packet  
   - Action: Leave QR after every service call
   - Result: 10% customers save contact for future needs
   - Outcome: Skip 30% platform commission on repeat business
   - **ROI: Direct commission savings of ₹1000s monthly**

### Long-term Relationship Building
- **WhatsApp Business Integration:** Product catalogs, payment links, customer groups
- **Recurring Revenue Streams:** Weekly/monthly service contracts
- **Referral Generation:** Satisfied customers share contact with friends
- **Brand Building:** Personal reputation independent of platforms

The platform handles base URL generation, QR image uploads, packet states (setup pending/done, configuration pending/done), dynamic redirections, and basic business tracking for sales and revenue.
Key Features

* Packet Creation: Generate packets with unique IDs and base URLs (e.g., kyuaar.com/packet/[id]). Specify the number of QRs in the packet (1-100). Auto-generate TWO QR codes per packet: Main QR for customer scans and Master QR for updates. Initial state: Setup Pending.

* Dual QR System:
  - **Main QR**: Customer-facing QR with base URL kyuaar.com/packet/PKT-123 for scans and redirects
  - **Master QR**: Update QR with secret URL kyuaar.com/manage/MGT-ABC789 for configuration changes
  - Both QRs auto-generated with user's default style settings during packet creation
  - Master QR ID is completely unrelated to main packet ID for security

* QR Upload and Management: After packet creation, admins can view and download both Main and Master QR images from the dashboard. Both QRs are auto-generated and ready for printing. Update state to Setup Done on successful generation.
* Packet States:

Setup Pending: Packet created but no QR image uploaded.
Setup Done: QR image uploaded and ready for distribution/sale.
Configuration Pending: Packet marked as sold (offline), ready for customer configuration via first scan.
Configuration Done: Customer has scanned and set the redirect (e.g., WhatsApp number or custom URL).


* Configuration Journey:

**INITIAL CUSTOMER SETUP FLOW**: When customer scans Main QR → goes to kyuaar.com/packet/PKT-123 → we check packet state:

If Setup Pending: Show error page ("Packet not ready").
If Setup Done but Configuration Pending: Customer sees config page on their mobile to enter/validate phone number (e.g., +919166900151) or custom URL. After they submit, we set redirect in DB to wa.me/[number] or custom URL, then update state to Configuration Done.
If Configuration Done: All QRs in packet redirect from base URL to the configured destination URL.

**MASTER QR UPDATE FLOW**: When customer scans Master QR → goes to kyuaar.com/manage/MGT-ABC789 → always shows update page:

- Customer can modify existing WhatsApp number or custom URL
- Same validation and UI as initial configuration 
- Updates apply immediately to all QRs in the packet
- Rate limited to prevent abuse (e.g., max 3 updates per day)
- No authentication required - physical Master QR access is the security

**SECURITY MODEL**: 
- Master QR ID (MGT-ABC789) is cryptographically unrelated to main packet ID (PKT-123)
- Impossible to derive Master URL from scanning Main QR
- Physical security: Master QR hidden behind tamper-evident seal
- Admin backup: Packet password stored for customer support cases

IMPORTANT: All QRs in the packet have the SAME base URL and redirect to the SAME destination. Updates via Master QR affect ALL QRs in that packet instantly.




* Customer Lifecycle Flows:

Offline Sale: Admin marks packet as sold in dashboard (e.g., via button), enters buyer details (name, email, price paid). State changes to Configuration Pending. Optionally print/ship packet with instructions to scan for setup.
Post-Sale: Customer receives packet, scans QR (opens config page on mobile), sets redirect. System logs this and updates to Configuration Done.
Updates: Customers can re-scan to edit redirect if needed (admin-configurable).


* User Journey (Customer's Voice): "Bought 25 QR stickers from Kyuaar offline. Admin had already generated QRs externally with the base URL and uploaded them. I scanned one QR to set my WhatsApp on my phone – simple form. Now, ALL 25 QRs redirect to my WhatsApp when customers scan them from my shop. Dashboard shows packet is configured!"

CLARIFICATION: Admin can EITHER generate QRs in-app OR upload externally generated QR images. Customer only configures where the QRs redirect to.
* Business Model: Sell packets offline. Track sales, pricing, and revenue in admin dashboard for simple business operations.

QR Code Generation System
Kyuaar includes a built-in QR code generator accessible via the "Generate QR" navigation menu item.

* Custom QR Generator: Dedicated page at /qr/generate with comprehensive styling options
* Live Preview: Real-time preview updates as settings change (debounced for performance)
* Style Customization:
  - Data Dot Shapes: Square, Rounded, Circle, Vertical Bars, Horizontal Bars
  - Corner/Eye Patterns: Square, Circle, Rounded (independent from data dots)
  - Color Options: Solid colors, Radial gradients, Square gradients
  - Size Controls: Module size (5-20px), Border width (1-10 modules)
* Style Presets: Quick-apply presets (Default, Rounded, Circular, Gradient styles, Bars)
* URL Input: Custom URL or auto-populate from existing packet base URLs
* Firebase Integration: Generated QRs automatically saved to Firebase Storage with metadata
* Download Options: PNG download, Copy to clipboard functionality
* Backend: Python qrcode[pil] library with StyledPilImage for advanced customization
* API Endpoints:
  - /api/qr/generate: Generate QR with custom settings
  - /api/qr/save: Save generated QR to Firebase
  - /api/qr/presets: Get available style presets
  - /api/qr/packet/<id>: List QRs generated for specific packet
* Database: QR metadata stored in Firestore 'qr_codes' collection with packet links, URLs, settings, and creation timestamps

Tech Stack Requirements

* Backend: Python Flask for API, routing, DB management.
* Frontend: HTML, CSS, JS. Use shadcn/ui core components ONLY (integrate via CDN like unpkg.com/shadcn-ui for buttons, cards, selects, tables – no custom hardcoded components). Use Phosphor icons where required. Do not hardcode design CSS manually ever; always use off-the-shelf shadcn/ui components and their built-in theming options.
* Database: Firebase Firestore. Store packet data including unique ID, base URL, QR count, uploaded image URLs (in Firebase Storage), redirect config, states (setup/config), sale details (buyer name, price, date sold), and scan logs.
* Image Handling: Use Firebase Storage for uploading and serving QR images. BOTH external QR upload AND in-app QR generation are supported via Flask forms and Firebase SDK.
* QR Code Generation: Built-in custom QR generator with Python qrcode library supporting style customization (shapes, colors, gradients, corner patterns). Generated QRs saved to Firebase with metadata linking to URLs and packets.
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
Generate QR: Use built-in QR generator (accessible via "Generate QR" menu) to create custom styled QR codes for packets or any URL. Generated QRs auto-saved to Firebase with metadata.
Mark as Sold: For Setup Done packets, button/form to mark sold: Enter buyer name/email, sale price (default from creation or editable), date. Update state to Configuration Pending. Log for revenue tracking.
List/Edit: Table of packets with columns: ID, Base URL, QR Count, State (Setup Pending/Done, Config Pending/Done), Sale Price, Buyer, Redirect URL, Uploaded Image Preview. Actions: Edit details, reset states/redirects, delete.


* Sales and Pricing Configurations:

PRICING CONFIG IS SIMPLE: Set how much we'll sell this packet for. That's it. During packet creation or marking sold, input field for sale price per packet (e.g., $10 for 25 QRs). This is the price we charge the customer for the entire packet.
Revenue Tracking: Dashboard section with total revenue, sales history table (packet ID, buyer, price, date), basic charts (use simple JS like Chart.js via CDN for monthly earnings).
Minimal Business Flows:

Offline Sale Flow: Create packet → Upload QR OR Generate QR (via built-in generator) → Mark as Sold (enter details) → Email buyer instructions (auto-generate with base URL for their reference).
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