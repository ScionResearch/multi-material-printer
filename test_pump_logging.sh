#!/bin/bash
# Test script for pump I2C logging verification
# Tests a short pump run and displays detailed I2C communication logs

echo "=== Pump I2C Logging Test ==="
echo "This will run Pump A forward for 3 seconds with detailed I2C logging"
echo ""

cd /home/pidlp/pidlp/multi-material-printer/src/controller

echo "Starting pump test..."
python3 mmu_control.py A F 3

echo ""
echo "=== Test Complete ==="
echo "Check the output above for:"
echo "  [I2C] MotorKit initialization messages"
echo "  [I2C] Controller address and stepper number mapping"
echo "  [I2C] Motor release confirmations"
echo "  [PUMP] Step count and timing statistics"
