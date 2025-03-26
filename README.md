# VibeWear

VibeWear is an e-commerce clothing website built using Django. It provides a seamless shopping experience with user authentication, product listing, and essential e-commerce features.

## Features
- **User Authentication:** Secure login and signup for new users.
- **Account Management:** Users can manage their profiles.
- **Product Listing:** Displays a list of clothing products with pagination.
- **Shop Section:** Users can browse and explore various categories.
- **About & Contact Section:** Provides details about the business and a way to contact support.

## Technologies Used
- **Backend:** Django (Python)
- **Frontend:** HTML, CSS, JavaScript
- **Database:** MySQL

## Installation
1. Clone the repository:
   ```sh
   git clone https://github.com/yourusername/vibewear.git
   cd vibewear
   ```
2. Create a virtual environment and activate it:
   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```
3. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
4. Apply migrations:
   ```sh
   python manage.py migrate
   ```
5. Create a superuser:
   ```sh
   python manage.py createsuperuser
   ```
6. Run the development server:
   ```sh
   python manage.py runserver
   ```

## Usage
- Open `http://127.0.0.1:8000/` in your browser.
- Register or log in to start shopping.
- Browse products and manage your account.

## Future Enhancements
- Implement a shopping cart and checkout system.
- Add payment gateway integration.
- Improve UI/UX with advanced styling.
- Enable product search and filtering.

## License
This project is open-source and available under the MIT License.

## Contact
For any inquiries or feedback, feel free to contact [Your Email] or visit our website.

