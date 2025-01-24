const form = document.getElementById("credentials-form");
if (form) {
    form.addEventListener("submit", function (e) {
        e.preventDefault(); // Prevent default form submission behavior

        const email = document.getElementById("vt_email").value;
        const username = email.split("@")[0]; // Extract username from email
        const password = document.getElementById("vt_password").value;

        // Save email in local storage to use in the processing page
        localStorage.setItem("email", email);

        // Redirect to the processing page
        window.location.href = "/processing";

        // Send form data to the backend asynchronously
        fetch("/submit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                vt_email: email,
                vt_username: username,
                vt_password: password,
            }),
        })
            .then((response) => {
                if (!response.ok) {
                    throw new Error("Failed to submit form");
                }
                return response.json();
            })
            .then((data) => {
                if (data.redirect_url) {
                    window.location.href = data.redirect_url; // Redirect to the dashboard
                }
            })
            .catch((error) => {
                console.error("Error during form submission:", error);
            });
    });
}
