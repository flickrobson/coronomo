USE coronomo;

# Bluetooth key exchanged when in contact
CREATE TABLE one_time_password
(
  time_added   DATETIME NOT NULL,
  password     VARCHAR(8) NOT NULL,
  PRIMARY KEY(password)
);

# Key received from health official
CREATE TABLE diagnosis_keys
(
  diag_id INT AUTO_INCREMENT NOT NULL,
  temp_exposure_key BLOB NOT NULL,
  en_interval_num   INT NOT NULL,
  PRIMARY KEY(diag_id)
);
