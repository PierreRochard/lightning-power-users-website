DROP TRIGGER IF EXISTS inbound_capacity_request_notify_update ON inbound_capacity_request;
CREATE TRIGGER inbound_capacity_request_notify_update
AFTER UPDATE ON inbound_capacity_request
FOR EACH ROW EXECUTE PROCEDURE table_notify();

DROP TRIGGER IF EXISTS inbound_capacity_request_notify_insert ON inbound_capacity_request;
CREATE TRIGGER inbound_capacity_request_notify_insert
AFTER INSERT ON inbound_capacity_request
FOR EACH ROW EXECUTE PROCEDURE table_notify();

DROP TRIGGER IF EXISTS inbound_capacity_request_notify_delete ON inbound_capacity_request;
CREATE TRIGGER inbound_capacity_request_notify_delete
AFTER DELETE ON inbound_capacity_request
FOR EACH ROW EXECUTE PROCEDURE table_notify();

DROP TRIGGER IF EXISTS invoices_notify_update ON invoices;
CREATE TRIGGER invoices_notify_update
  AFTER UPDATE ON invoices
  FOR EACH ROW EXECUTE PROCEDURE table_notify();

DROP TRIGGER IF EXISTS invoices_notify_insert ON invoices;
CREATE TRIGGER invoices_notify_insert
  AFTER INSERT ON invoices
  FOR EACH ROW EXECUTE PROCEDURE table_notify();

DROP TRIGGER IF EXISTS invoices_notify_delete ON invoices;
CREATE TRIGGER invoices_notify_delete
  AFTER DELETE ON invoices
  FOR EACH ROW EXECUTE PROCEDURE table_notify();

DROP TRIGGER IF EXISTS pending_open_channels_notify_update ON pending_open_channels;
CREATE TRIGGER pending_open_channels_notify_update
  AFTER UPDATE ON pending_open_channels
  FOR EACH ROW EXECUTE PROCEDURE table_notify();

DROP TRIGGER IF EXISTS pending_open_channels_notify_insert ON pending_open_channels;
CREATE TRIGGER pending_open_channels_notify_insert
  AFTER INSERT ON pending_open_channels
  FOR EACH ROW EXECUTE PROCEDURE table_notify();

DROP TRIGGER IF EXISTS pending_open_channels_notify_delete ON pending_open_channels;
CREATE TRIGGER pending_open_channels_notify_delete
  AFTER DELETE ON pending_open_channels
  FOR EACH ROW EXECUTE PROCEDURE table_notify();


DROP TRIGGER IF EXISTS forwarding_events_notify_insert ON forwarding_events;
CREATE TRIGGER forwarding_events_notify_insert
  AFTER INSERT ON forwarding_events
  FOR EACH ROW EXECUTE PROCEDURE table_notify();