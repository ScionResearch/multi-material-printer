#include "configmanager.h"
#include <QDir>
#include <QDebug>
#include <QFileInfo>

ConfigManager& ConfigManager::instance()
{
    static ConfigManager instance;
    return instance;
}

ConfigManager::ConfigManager()
{
    m_appDir = QCoreApplication::applicationDirPath();
    m_configPath = m_appDir + "/../config/network_settings.ini";
    loadConfiguration();
}

void ConfigManager::loadConfiguration()
{
    // Check if config file exists, if not try to copy from template
    if (!QFileInfo::exists(m_configPath)) {
        QString templatePath = m_appDir + "/../config/network_settings.ini.template";
        if (QFileInfo::exists(templatePath)) {
            QFile::copy(templatePath, m_configPath);
            qDebug() << "Created config file from template:" << m_configPath;
        } else {
            qWarning() << "Neither config file nor template found!";
        }
    }
    
    m_settings = new QSettings(m_configPath, QSettings::IniFormat);
    qDebug() << "Loaded configuration from:" << m_configPath;
}

QString ConfigManager::getPrinterIP()
{
    if (!m_settings) return "192.168.4.2"; // Default fallback
    
    QString ip = m_settings->value("printer/ip_address", "").toString();
    if (ip.isEmpty()) {
        return "192.168.4.2"; // Default fallback for auto-discovery
    }
    return ip;
}

int ConfigManager::getPrinterPort()
{
    if (!m_settings) return 80;
    return m_settings->value("printer/port", 80).toInt();
}

int ConfigManager::getPrinterTimeout()
{
    if (!m_settings) return 10;
    return m_settings->value("printer/timeout", 10).toInt();
}

QString ConfigManager::getWiFiSSID()
{
    if (!m_settings) return "";
    return m_settings->value("wifi/ssid", "").toString();
}

QString ConfigManager::getWiFiPassword()
{
    if (!m_settings) return "";
    return m_settings->value("wifi/password", "").toString();
}

bool ConfigManager::isWiFiEnabled()
{
    if (!m_settings) return false;
    return m_settings->value("wifi/enabled", false).toBool();
}

QString ConfigManager::getAPSSID()
{
    if (!m_settings) return "ScionMMU";
    return m_settings->value("access_point/ssid", "ScionMMU").toString();
}

QString ConfigManager::getAPPassword()
{
    if (!m_settings) return "scionmmu123";
    return m_settings->value("access_point/password", "scionmmu123").toString();
}

QString ConfigManager::getAPIPAddress()
{
    if (!m_settings) return "192.168.4.1";
    return m_settings->value("access_point/ip_address", "192.168.4.1").toString();
}

bool ConfigManager::isAPEnabled()
{
    if (!m_settings) return true;
    return m_settings->value("access_point/enabled", true).toBool();
}

QString ConfigManager::getScriptPath(const QString& scriptName)
{
    return m_appDir + "/../src/controller/" + scriptName;
}

QString ConfigManager::getConfigPath()
{
    return m_appDir + "/../config";
}

QString ConfigManager::getRecipePath()
{
    return m_appDir + "/../config/recipe.txt";
}