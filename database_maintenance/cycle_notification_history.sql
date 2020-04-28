-- Create new notification_history table and primary key.
CREATE TABLE notification_history_pivot AS SELECT * FROM notification_history WHERE 1=2;
ALTER TABLE notification_history_pivot ADD PRIMARY KEY (id);

-- CREATE TRIGGER update_pivot BEFORE UPDATE ON notification_history
create trigger to update notification_history_pivot when update to notification_history

create foreign key constraints in notification_history_pivot

insert data into notification_history_pivot in batches

create remaining indices on notification_history_pivot

-- Run basic sanity checks on data in notification_history_pivot, ensuring same number of entries present in notification_history and notification_history_pivot

ALTER TABLE notification_history RENAME TO notification_history_old;
-- TODO: Drop constraints on notification_history_old
ALTER TABLE notification_history_pivot RENAME TO notification_history;

-- Run sanity checks on data in notification_history_pivot
-- 1. Ensure same number of entries in notification_history and notification_history_pivot
-- If not then reconcile entries and add remaining entries to notification_history

-- When sure data in new notification_history table are ok:
ALTER TABLE notification_history_old DROP CONSTRAINT notification_history_pkey; -- May not need this step.
DROP TABLE notification_history_old;

-- Must rename primary key on new notification_history table or will get issues running this script in the future.
-- This is not very nice.
ALTER TABLE notification_history DROP CONSTRAINT notification_history_pivot_pkey;
ALTER TABLE notification_history ADD PRIMARY KEY (id); -- Will create a new primary key named "notification_history_pkey".

-- Note that the only impact of these changes
