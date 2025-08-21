#ifndef CONFIGMANAGER_H
#define CONFIGMANAGER_H

#include <QString>
#include <QSettings>
#include <QCoreApplication>

class ConfigManager
{
public:
    static ConfigManager& instance();
    
    // Network settings
    QString getPrinterIP();
    int getPrinterPort();
    int getPrinterTimeout();
    
    // WiFi settings
    QString getWiFiSSID();
    QString getWiFiPassword();
    bool isWiFiEnabled();
    
    // Access Point settings
    QString getAPSSID();
    QString getAPPassword();
    QString getAPIPAddress();
    bool isAPEnabled();
    
    // Paths
    QString getScriptPath(const QString& scriptName);
    QString getConfigPath();
    QString getRecipePath();
    
private:
    ConfigManager();
    ConfigManager(const ConfigManager&) = delete;
    ConfigManager& operator=(const ConfigManager&) = delete;
    
    void loadConfiguration();
    QString m_configPath;
    QSettings* m_settings;
    QString m_appDir;
};

#endif // CONFIGMANAGER_H