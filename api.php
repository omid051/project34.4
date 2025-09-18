<?php
// تنظیم هدرها برای اطمینان از خروجی صحیح JSON و اجازه دسترسی از منابع دیگر (CORS)
header("Content-Type: application/json; charset=UTF-8");
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: POST, GET");
header("Access-Control-Allow-Headers: Content-Type, Access-Control-Allow-Headers, Authorization, X-Requested-With");

$SECRET_KEY = "secret";
$servername = "localhost";
$username = "user";
$password = "pass";
$dbname = "name";
// --------------------------------------------------------------------------

$auth_key = isset($_POST['secret_key']) ? $_POST['secret_key'] : '';
if ($auth_key !== $SECRET_KEY && $_SERVER['REQUEST_METHOD'] !== 'GET') {
    echo json_encode(['status' => 'error', 'message' => 'Authentication Failed.']);
    http_response_code(403);
    exit();
}

$conn = new mysqli($servername, $username, $password, $dbname);

if ($conn->connect_error) {
    echo json_encode(['status' => 'error', 'message' => 'Database connection failed: ' . $conn->connect_error]);
    http_response_code(500);
    exit();
}
$conn->set_charset("utf8mb4");

// ایجاد جدول کاربران در صورت عدم وجود
$sql_create_users_table = "CREATE TABLE IF NOT EXISTS users (
    id INT(10) UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    description TEXT,
    reg_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)";
$conn->query($sql_create_users_table);

// ایجاد جدول متقاضیان با فیلدهای جدید در صورت عدم وجود
// Changed `id` to not be AUTO_INCREMENT
$sql_create_applicants_table = "CREATE TABLE IF NOT EXISTS applicants (
    id INT(10) UNSIGNED NOT NULL PRIMARY KEY,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    description TEXT,
    phone_number VARCHAR(20),
    status VARCHAR(255) NOT NULL DEFAULT 'pending',
    visa_type ENUM('Ausbildung', 'Work', 'Student', 'Visit', 'Tourism', 'Legal', 'Doctor', 'Other') NOT NULL,
    is_visible TINYINT(1) NOT NULL DEFAULT 1,
    slot_selection ENUM('fastest', 'random', 'latest') NOT NULL DEFAULT 'random',
    creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reg_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
)";
$conn->query($sql_create_applicants_table);


// بررسی و افزودن ستون phone_number در صورت عدم وجود
$result = $conn->query("SHOW COLUMNS FROM `applicants` LIKE 'phone_number'");
if ($result->num_rows == 0) {
    $conn->query("ALTER TABLE `applicants` ADD `phone_number` VARCHAR(20) AFTER `description`");
}

// بررسی و افزودن ستون creation_date در صورت عدم وجود
$result = $conn->query("SHOW COLUMNS FROM `applicants` LIKE 'creation_date'");
if ($result->num_rows == 0) {
    $conn->query("ALTER TABLE `applicants` ADD `creation_date` TIMESTAMP DEFAULT CURRENT_TIMESTAMP AFTER `slot_selection`");
}

// بررسی و افزودن ستون slot_selection در صورت عدم وجود
$result = $conn->query("SHOW COLUMNS FROM `applicants` LIKE 'slot_selection'");
if ($result->num_rows == 0) {
    $conn->query("ALTER TABLE `applicants` ADD `slot_selection` ENUM('fastest', 'random', 'latest') NOT NULL DEFAULT 'random'");
}

// حذف ستون desired_date در صورت وجود
$result = $conn->query("SHOW COLUMNS FROM `applicants` LIKE 'desired_date'");
if ($result->num_rows > 0) {
    $conn->query("ALTER TABLE `applicants` DROP COLUMN `desired_date`");
}

// حذف ستون select_button در صورت وجود
$result = $conn->query("SHOW COLUMNS FROM `applicants` LIKE 'select_button'");
if ($result->num_rows > 0) {
    $conn->query("ALTER TABLE `applicants` DROP COLUMN `select_button`");
}


$action = isset($_REQUEST['action']) ? $_REQUEST['action'] : '';

if ($_SERVER['REQUEST_METHOD'] === 'POST' && $action === 'login') {
    $username = $_POST['username'];
    $password = $_POST['password'];
    $stmt = $conn->prepare("SELECT * FROM users WHERE username = ? AND password = ?");
    $stmt->bind_param("ss", $username, $password);
    $stmt->execute();
    $result = $stmt->get_result();
    if ($result->num_rows > 0) {
        echo json_encode(['status' => 'success', 'message' => 'Login successful.']);
    } else {
        echo json_encode(['status' => 'error', 'message' => 'Invalid credentials.']);
    }
    $stmt->close();
}
elseif ($_SERVER['REQUEST_METHOD'] === 'GET' && $action === 'get_applicants') {
    $result = $conn->query("SELECT id, email, password, description, status, visa_type, is_visible, slot_selection FROM applicants WHERE is_visible = 1 ORDER BY id DESC");
    $applicants = [];
    if ($result && $result->num_rows > 0) {
        while($row = $result->fetch_assoc()) {
            $applicants[] = $row;
        }
    }
    echo json_encode($applicants);

} elseif ($_SERVER['REQUEST_METHOD'] === 'POST' && $action === 'update_status') {
    $id = $_POST['id'];
    $status = $_POST['status'];
    $username = isset($_POST['username']) ? $_POST['username'] : '';

    $stmt = $conn->prepare("SELECT status FROM applicants WHERE id = ?");
    $stmt->bind_param("i", $id);
    $stmt->execute();
    $result = $stmt->get_result();
    $current_status = $result->fetch_assoc()['status'];

    if (strpos($status, 'Booked by') !== false) {
        $new_status = $status;
    }
    else if ($status === 'pending' && strpos($current_status, 'Booked by') !== false) {
        $new_status = 'pending';
    }
    else if (strpos($current_status, 'In Progress by') !== false) {
        if ($status == 'pending') {
            // Remove user from the list
            $users = array_filter(explode(', ', str_replace('In Progress by ', '', $current_status)), function($u) use ($username) {
                return $u !== $username;
            });
            if (empty($users)) {
                $new_status = 'pending';
            } else {
                $new_status = 'In Progress by ' . implode(', ', $users);
            }
        } else {
            // Add user to the list
            $users = explode(', ', str_replace('In Progress by ', '', $current_status));
            if (!in_array($username, $users)) {
                $users[] = $username;
            }
            $new_status = 'In Progress by ' . implode(', ', $users);
        }
    } else {
        if ($status == 'in_progress') {
            $new_status = 'In Progress by ' . $username;
        } else {
            $new_status = $status;
        }
    }


    $stmt = $conn->prepare("UPDATE applicants SET status = ? WHERE id = ?");
    $stmt->bind_param("si", $new_status, $id);
    if ($stmt->execute()) {
        echo json_encode(['status' => 'success', 'message' => 'Status updated successfully.']);
    } else {
        echo json_encode(['status' => 'error', 'message' => 'Failed to update status.']);
    }
    $stmt->close();
} elseif ($_SERVER['REQUEST_METHOD'] === 'POST' && $action === 'add_applicant') {
    // ID is now manually provided
    $stmt = $conn->prepare("INSERT INTO applicants (id, email, password, description, phone_number, visa_type, is_visible, slot_selection) VALUES (?, ?, ?, ?, ?, ?, ?, ?)");
    $stmt->bind_param("isssssis", $_POST['id'], $_POST['email'], $_POST['password'], $_POST['description'], $_POST['phone_number'], $_POST['visa_type'], $_POST['is_visible'], $_POST['slot_selection']);
    if ($stmt->execute()) {
        echo json_encode(['status' => 'success', 'message' => 'Applicant added successfully.']);
    } else {
        // Provide more specific error for duplicate ID
        if ($conn->errno == 1062) { // 1062 is the error code for duplicate entry
             echo json_encode(['status' => 'error', 'message' => 'Failed to add applicant. The ID or Email already exists.']);
        } else {
            echo json_encode(['status' => 'error', 'message' => 'Failed to add applicant. Error: ' . $stmt->error]);
        }
    }
    $stmt->close();

} elseif ($_SERVER['REQUEST_METHOD'] === 'POST' && $action === 'update_applicant') {
    // ID can be updated as well
    $stmt = $conn->prepare("UPDATE applicants SET email = ?, password = ?, description = ?, phone_number = ?, visa_type = ?, is_visible = ?, slot_selection = ? WHERE id = ?");
    $stmt->bind_param("sssssisi", $_POST['email'], $_POST['password'], $_POST['description'], $_POST['phone_number'], $_POST['visa_type'], $_POST['is_visible'], $_POST['slot_selection'], $_POST['id']);
    if ($stmt->execute()) {
        echo json_encode(['status' => 'success', 'message' => 'Applicant updated successfully.']);
    } else {
         if ($conn->errno == 1062) {
             echo json_encode(['status' => 'error', 'message' => 'Failed to update applicant. The Email already exists for another applicant.']);
        } else {
            echo json_encode(['status' => 'error', 'message' => 'Failed to update applicant. Error: ' . $stmt->error]);
        }
    }
    $stmt->close();
}
else {
    echo json_encode(['status' => 'error', 'message' => 'Invalid action or request method.']);
    http_response_code(400);
}

$conn->close();

?>