## ManageIt
**🍽️ Mess Management System**
A full-stack web application built using Flask and MySQL for efficient and transparent management of mess operations in my institute. This system enables students, mess officials, and admins to interact with the mess system seamlessly through role-based access, feedback systems, dynamic menus, payment tracking, mess switching, and more.

📌 Features
🔐 Authentication and Roles
Students: Submit feedback, view mess insights, switch mess (if capacity allows).

Mess Officials: Enter food data (prepared, wasted, remaining), update menus(non-veg), mark physical payments, see insights from waste data entered.

Admin: Full control of the system – monitor mess status, view insights incl. payments, feedback data, waste data, controls mess switching for students, update main menu, ...

**📊 Feedback System**
Menu-wise(veg and non-veg) feedback for each meal with options to add comments.

Separate feedback tables per mess with both summary and detailed data.

Insightful data over the past month for each student upon login.

**🍛 Menu Management**
Default veg and non-veg menu system.

Non-veg menu is not part of the regular plan – visible for purchase and served only on specific floors.

Veg menu updates apply only for the current day and revert back automatically.

**🔁 Mess Switching**
Students can switch messes based on real-time capacity availability.

First-come-first-serve policy.

No approval required – completely dynamic and student-friendly (admin have to approve it for specific time usually at the starting of each month for about 5-7 days).

**📅 Week Tracking**
System follows odd/even week pattern that continues across months.

Enables better planning and insights based on alternating weekly menus.

**📈 Mess Data Insights**
Mess officials input data for food prepared, wasted, and remaining.

Dashboard shows trends, graphs, and food wastage analytics.

Helps improve efficiency and minimize food waste.

**🛠️ Tech Stack**
Layer	Technology
Backend	    Python (Flask)
Frontend	HTML, CSS, JS
Database	MySQL
Auth	    Flask-Login / Session
Graphs	    Chart.js / JS libraries
Hosting     Render

**🔐 Role-Based Routes**
Role	        Access
Student	        Feedback, mess insights, switch mess
Mess_Official	Update food data, mark payments, update menu, insights from waste data
Admin	        Manage everything

To view the website, go to the link: https://manageit-ca07.onrender.com

If you want to see more, i have attached the report that includes all the details for this website.

📄 License
This project is licensed under the MIT License.

