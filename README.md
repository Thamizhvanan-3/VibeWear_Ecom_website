# ✨ VibeWear 👕🛍️

VibeWear is an **e-commerce clothing website** built using Django. It provides a seamless shopping experience with user authentication, product listing, and essential e-commerce features.

## 🚀 Features
- 🔐 **User Authentication:** Secure signup and login with either username or email. Duplicate usernames/emails are rejected case-insensitively.
- 🔑 **Password Management:** Password reset by email and password change while logged in.
- 👤 **Account Management:** Editable profile plus multiple saved delivery addresses.
- 🛒 **Cart:** Guest carts are stored in the session and merged into the account cart after login. Quantities are validated against live stock.
- 📦 **Checkout & Orders:** Cash-on-delivery checkout with server-side totals, transactional stock updates, order IDs, statuses, and order history.
- 👕 **Product Catalog:** Categories and subcategories, multiple images, size/color/stock variants, and original/discounted pricing.
- ⭐ **Merchandising:** Featured, new-arrival, and best-seller sections.
- 🔍 **Shop Tools:** Search, category/size/color filters, sorting, and pagination.
- ❤️ **Wishlist:** Save products and move them to the cart later.
- 📊 **Admin Dashboard:** Sales/order statistics, low-stock alerts, inline product images/variants, and order status actions.
- 📞 **About & Contact Section:** Provides details about the business and a way to contact support.

## 🛠️ Technologies Used
- 🖥️ **Backend:** Django 6.0 (Python)
- 🎨 **Frontend:** HTML, CSS, JavaScript
- 🗄️ **Database:** SQLite (development default)

## 📌 Installation
1. **Clone the repository:**
   ```sh
   git clone https://github.com/yourusername/vibewear.git
   cd vibewear
   ```
2. **Create a virtual environment and activate it:**
   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```
3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
4. **Apply migrations:**
   ```sh
   python manage.py migrate
   ```
   This also seeds the starter catalog and user profiles without deleting existing rows.
5. **Create a superuser:**
   ```sh
   python manage.py createsuperuser
   ```
6. **Run the development server:**
   ```sh
   python manage.py runserver
   ```

> **Notes**
> - Uploaded product images are stored in `media/` and served automatically in development.
> - Password-reset emails use Django's console backend in development, so the reset link is printed in the terminal.
> - Run the test suite with `python manage.py test`.

## 🎯 Usage
- Open `http://127.0.0.1:8000/` in your browser.
- 🔑 Register or log in to start shopping. Items added as a guest are kept when you log in.
- 🛍️ Browse the shop, filter by category/size/color, and add products to your cart or wishlist.
- 📦 Check out with cash on delivery and follow your order from the dashboard.
- 🛠️ Manage the catalog, stock, and orders from `/admin/`.

## 🔮 Future Enhancements
- 💳 Add **online payment gateway** integration.
- 🚚 Add shipment tracking and delivery integrations.
- 📧 Send order confirmation emails.
- 🌍 Add multi-currency and international shipping support.

## 📜 License
This project is open-source and available under the **MIT License**.

## 📧 Contact
For any inquiries or feedback, feel free to contact [Your Email] or visit our website. 🌐

