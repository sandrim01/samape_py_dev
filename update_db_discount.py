import os
from main import app, db
from sqlalchemy import Column, Numeric, text

def add_discount_columns():
    """Add discount-related columns to service_order table if they don't exist"""
    try:
        from models import ServiceOrder
        conn = db.engine.connect()
        
        # Check if discount_amount column exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='service_order' AND column_name='discount_amount'
        """))
        if result.rowcount == 0:
            # Add discount_amount column if it doesn't exist
            conn.execute(text('ALTER TABLE service_order ADD COLUMN discount_amount NUMERIC(10, 2) DEFAULT 0'))
            print("Added discount_amount column to service_order table")
        
        # Check if original_amount column exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='service_order' AND column_name='original_amount'
        """))
        if result.rowcount == 0:
            # Add original_amount column if it doesn't exist
            conn.execute(text('ALTER TABLE service_order ADD COLUMN original_amount NUMERIC(10, 2)'))
            print("Added original_amount column to service_order table")
            
            # Update original_amount with invoice_amount for existing records
            conn.execute(text("""
                UPDATE service_order 
                SET original_amount = invoice_amount 
                WHERE invoice_amount IS NOT NULL
            """))
            print("Updated original_amount values for existing records")
            
        conn.close()
        print("Database update complete")
        return True
    except Exception as e:
        print(f"Error updating database: {e}")
        return False

if __name__ == "__main__":
    with app.app_context():
        add_discount_columns()