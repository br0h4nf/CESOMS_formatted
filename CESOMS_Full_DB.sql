-- MySQL dump 10.13  Distrib 8.0.45, for Win64 (x86_64)
--
-- Host: localhost    Database: campus_event_db
-- ------------------------------------------------------
-- Server version	8.0.45

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `academic_term`
--

DROP TABLE IF EXISTS `academic_term`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `academic_term` (
  `TermID` int NOT NULL,
  `TermName` varchar(50) NOT NULL,
  `StartDate` date NOT NULL,
  `EndDate` date NOT NULL,
  PRIMARY KEY (`TermID`),
  CONSTRAINT `academic_term_chk_1` CHECK ((`StartDate` <= `EndDate`))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `academic_term`
--

LOCK TABLES `academic_term` WRITE;
/*!40000 ALTER TABLE `academic_term` DISABLE KEYS */;
INSERT INTO `academic_term` VALUES (1,'Fall 2026','2026-08-20','2026-12-10'),(2,'Spring 2027','2027-01-15','2027-05-05'),(3,'Summer 2027','2027-06-01','2027-08-01');
/*!40000 ALTER TABLE `academic_term` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `administrator`
--

DROP TABLE IF EXISTS `administrator`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `administrator` (
  `AdminID` int NOT NULL,
  `FirstName` varchar(50) NOT NULL,
  `LastName` varchar(50) NOT NULL,
  `Email` varchar(100) NOT NULL,
  `Department` varchar(100) DEFAULT NULL,
  `AdminStatus` varchar(20) NOT NULL,
  PRIMARY KEY (`AdminID`),
  UNIQUE KEY `Email` (`Email`),
  CONSTRAINT `administrator_chk_1` CHECK ((`AdminStatus` in (_utf8mb4'Active',_utf8mb4'Inactive')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `administrator`
--

LOCK TABLES `administrator` WRITE;
/*!40000 ALTER TABLE `administrator` DISABLE KEYS */;
INSERT INTO `administrator` VALUES (1,'Admin','One','admin1@vt.edu','CS','Active'),(2,'Admin','Two','admin2@vt.edu','IT','Active'),(3,'Admin','Three','admin3@vt.edu','Math','Active'),(4,'Admin','Four','admin4@vt.edu','Business','Active'),(5,'Admin','Five','admin5@vt.edu','Engineering','Active'),(906597555,'Brad','Admin','bradleyf23@vt.edu','CS','Active'),(906618852,'Surafail','Asheber','surafail2a@vt.edu','Full_Admin','Active');
/*!40000 ALTER TABLE `administrator` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `app_user`
--

DROP TABLE IF EXISTS `app_user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `app_user` (
  `UserID` int NOT NULL AUTO_INCREMENT,
  `AccountType` varchar(20) NOT NULL,
  `AccountRefID` varchar(50) NOT NULL,
  `PasswordHash` varchar(255) NOT NULL,
  `CreatedAt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `LastPasswordChangedAt` datetime DEFAULT NULL,
  PRIMARY KEY (`UserID`),
  UNIQUE KEY `uq_app_user_account` (`AccountType`,`AccountRefID`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `app_user`
--

LOCK TABLES `app_user` WRITE;
/*!40000 ALTER TABLE `app_user` DISABLE KEYS */;
INSERT INTO `app_user` VALUES (1,'student','9065','scrypt:32768:8:1$WuGRv2aghd14ZkAa$654e322897219458e421171c78812a2c27b110b34ca13726d5c6409a2a8c5970129e87024e1ffd71ebd6e29126c1aeed63c75339d345bf0e3d9bc53e321eca76','2026-04-21 23:05:27','2026-04-21 23:05:27'),(2,'admin','1','scrypt:32768:8:1$YELMZWc8tKFzjFO4$1d7e78f6a501dcaaad18c06f555de230bb9d4c1d6b5d63d680f4f461cd1923abb507b25fd4103283502342979d4ce35805b03cdc9eb7e51e87097a7fc1b0096b','2026-04-21 23:11:52','2026-04-21 23:11:52'),(3,'student','0458','scrypt:32768:8:1$AgoPShSYuhrkhX6R$3566f3e9c1a3a475ada3f2948577c7651a093ac0c03bab21683afa5b60493c4ff24183068bb655df6431fa42ee8e47a04a1412afa8c5e9fecc895021be70ba85','2026-04-22 12:56:18','2026-04-22 12:56:18'),(4,'admin','906618852','scrypt:32768:8:1$LZsTn9o8MQBPlNwF$ee2d2e760f97022cfb025becd33343dbdf6155079ea8f78cf26872301cc957cf5294487c5bd7dfa811c424154ebee04f560a8152bed59e9c92b75b034eeb9cd8','2026-04-22 17:38:27','2026-04-22 17:38:27');
/*!40000 ALTER TABLE `app_user` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `approval`
--

DROP TABLE IF EXISTS `approval`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `approval` (
  `EventID` int NOT NULL,
  `SubmittedByOfficerStudentID` int DEFAULT NULL,
  `SubmittedByOfficerOrgID` int DEFAULT NULL,
  `SubmittedByOfficerStartDate` date DEFAULT NULL,
  `ReviewedByAdminID` int DEFAULT NULL,
  `SubmittedAt` datetime NOT NULL,
  `ReviewedAt` datetime DEFAULT NULL,
  `DecisionStatus` varchar(20) NOT NULL,
  `DecisionNotes` text,
  PRIMARY KEY (`EventID`),
  KEY `ReviewedByAdminID` (`ReviewedByAdminID`),
  KEY `SubmittedByOfficerStudentID` (`SubmittedByOfficerStudentID`,`SubmittedByOfficerOrgID`,`SubmittedByOfficerStartDate`),
  CONSTRAINT `approval_ibfk_1` FOREIGN KEY (`EventID`) REFERENCES `event` (`EventID`),
  CONSTRAINT `approval_ibfk_2` FOREIGN KEY (`ReviewedByAdminID`) REFERENCES `administrator` (`AdminID`),
  CONSTRAINT `approval_ibfk_3` FOREIGN KEY (`SubmittedByOfficerStudentID`, `SubmittedByOfficerOrgID`, `SubmittedByOfficerStartDate`) REFERENCES `organization_officer` (`StudentID`, `OrgID`, `StartDate`),
  CONSTRAINT `approval_chk_1` CHECK ((`DecisionStatus` in (_utf8mb4'Pending',_utf8mb4'Approved',_utf8mb4'Rejected'))),
  CONSTRAINT `approval_chk_2` CHECK (((`ReviewedAt` is null) or (`SubmittedAt` <= `ReviewedAt`)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `approval`
--

LOCK TABLES `approval` WRITE;
/*!40000 ALTER TABLE `approval` DISABLE KEYS */;
INSERT INTO `approval` VALUES (1,1,1,'2026-01-01',1,'2026-08-01 09:00:00','2026-08-02 09:00:00','Approved','OK'),(2,2,2,'2026-01-01',2,'2026-08-01 09:00:00','2026-08-02 09:00:00','Approved','OK'),(3,3,3,'2026-01-01',3,'2026-08-01 09:00:00','2026-08-02 09:00:00','Approved','OK'),(4,4,4,'2026-01-01',4,'2026-08-01 09:00:00','2026-08-02 09:00:00','Approved','OK'),(5,5,5,'2026-01-01',5,'2026-08-01 09:00:00','2026-08-02 09:00:00','Approved','OK');
/*!40000 ALTER TABLE `approval` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `attendance`
--

DROP TABLE IF EXISTS `attendance`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `attendance` (
  `StudentID` int NOT NULL,
  `EventID` int NOT NULL,
  `CheckInTime` datetime DEFAULT NULL,
  `AttendanceFlag` varchar(20) NOT NULL,
  `RecordedByOfficerStudentID` int DEFAULT NULL,
  `RecordedByOfficerOrgID` int DEFAULT NULL,
  `RecordedByOfficerStartDate` date DEFAULT NULL,
  PRIMARY KEY (`StudentID`,`EventID`),
  KEY `EventID` (`EventID`),
  KEY `RecordedByOfficerStudentID` (`RecordedByOfficerStudentID`,`RecordedByOfficerOrgID`,`RecordedByOfficerStartDate`),
  CONSTRAINT `attendance_ibfk_1` FOREIGN KEY (`StudentID`) REFERENCES `student` (`StudentID`),
  CONSTRAINT `attendance_ibfk_2` FOREIGN KEY (`EventID`) REFERENCES `event` (`EventID`),
  CONSTRAINT `attendance_ibfk_3` FOREIGN KEY (`RecordedByOfficerStudentID`, `RecordedByOfficerOrgID`, `RecordedByOfficerStartDate`) REFERENCES `organization_officer` (`StudentID`, `OrgID`, `StartDate`),
  CONSTRAINT `attendance_chk_1` CHECK ((`AttendanceFlag` in (_utf8mb4'Present',_utf8mb4'Absent')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `attendance`
--

LOCK TABLES `attendance` WRITE;
/*!40000 ALTER TABLE `attendance` DISABLE KEYS */;
INSERT INTO `attendance` VALUES (1,1,'2026-09-01 18:05:00','Present',1,1,'2026-01-01'),(2,2,'2026-09-05 17:05:00','Present',2,2,'2026-01-01'),(3,3,'2026-09-10 16:10:00','Present',3,3,'2026-01-01'),(4,4,'2026-09-12 18:15:00','Present',4,4,'2026-01-01'),(5,5,'2026-09-15 15:05:00','Present',5,5,'2026-01-01');
/*!40000 ALTER TABLE `attendance` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `event`
--

DROP TABLE IF EXISTS `event`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `event` (
  `EventID` int NOT NULL,
  `OrgID` int NOT NULL,
  `LocationID` int NOT NULL,
  `CategoryID` int NOT NULL,
  `TermID` int NOT NULL,
  `Title` varchar(150) NOT NULL,
  `Description` text,
  `Capacity` int DEFAULT NULL,
  `StartDateTime` datetime NOT NULL,
  `EndDateTime` datetime NOT NULL,
  `EventStatus` varchar(20) NOT NULL,
  PRIMARY KEY (`EventID`),
  KEY `OrgID` (`OrgID`),
  KEY `LocationID` (`LocationID`),
  KEY `CategoryID` (`CategoryID`),
  KEY `TermID` (`TermID`),
  CONSTRAINT `event_ibfk_1` FOREIGN KEY (`OrgID`) REFERENCES `organization` (`OrgID`),
  CONSTRAINT `event_ibfk_2` FOREIGN KEY (`LocationID`) REFERENCES `location` (`LocationID`),
  CONSTRAINT `event_ibfk_3` FOREIGN KEY (`CategoryID`) REFERENCES `event_category` (`CategoryID`),
  CONSTRAINT `event_ibfk_4` FOREIGN KEY (`TermID`) REFERENCES `academic_term` (`TermID`),
  CONSTRAINT `event_chk_1` CHECK ((`Capacity` >= 0)),
  CONSTRAINT `event_chk_2` CHECK ((`StartDateTime` < `EndDateTime`)),
  CONSTRAINT `event_chk_3` CHECK ((`EventStatus` in (_utf8mb4'Draft',_utf8mb4'Submitted',_utf8mb4'Approved',_utf8mb4'Rejected',_utf8mb4'Scheduled',_utf8mb4'Completed',_utf8mb4'Cancelled')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `event`
--

LOCK TABLES `event` WRITE;
/*!40000 ALTER TABLE `event` DISABLE KEYS */;
INSERT INTO `event` VALUES (1,1,1,1,1,'Hack Night','Coding event',50,'2026-09-01 18:00:00','2026-09-01 21:00:00','Scheduled'),(2,2,2,2,1,'Finance Talk','Money tips',40,'2026-09-05 17:00:00','2026-09-05 19:00:00','Scheduled'),(3,3,3,3,1,'AI Competition','AI contest',60,'2026-09-10 16:00:00','2026-09-10 20:00:00','Scheduled'),(4,4,4,2,1,'Game Night','Fun games',100,'2026-09-12 18:00:00','2026-09-12 22:00:00','Scheduled'),(5,5,5,5,1,'Robotics Talk','Robots',30,'2026-09-15 15:00:00','2026-09-15 17:00:00','Scheduled'),(1234,6,5,3,2,'Monopoly!','RAAHHHHHH',5,'2026-04-09 17:31:00','2026-04-09 20:31:00','Scheduled');
/*!40000 ALTER TABLE `event` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `event_category`
--

DROP TABLE IF EXISTS `event_category`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `event_category` (
  `CategoryID` int NOT NULL,
  `CategoryName` varchar(100) NOT NULL,
  `Description` text,
  PRIMARY KEY (`CategoryID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `event_category`
--

LOCK TABLES `event_category` WRITE;
/*!40000 ALTER TABLE `event_category` DISABLE KEYS */;
INSERT INTO `event_category` VALUES (1,'Workshop','Learning'),(2,'Social','Fun'),(3,'Competition','Contest'),(4,'Meeting','General'),(5,'Seminar','Talk');
/*!40000 ALTER TABLE `event_category` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `location`
--

DROP TABLE IF EXISTS `location`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `location` (
  `LocationID` int NOT NULL,
  `LocationName` varchar(100) NOT NULL,
  `Building` varchar(100) DEFAULT NULL,
  `Room` varchar(50) DEFAULT NULL,
  `Address` varchar(200) DEFAULT NULL,
  `IsVirtual` tinyint(1) NOT NULL,
  `VirtualLink` varchar(255) DEFAULT NULL,
  `Capacity` int DEFAULT NULL,
  PRIMARY KEY (`LocationID`),
  CONSTRAINT `location_chk_1` CHECK ((`Capacity` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `location`
--

LOCK TABLES `location` WRITE;
/*!40000 ALTER TABLE `location` DISABLE KEYS */;
INSERT INTO `location` VALUES (1,'Room A','Goodwin','101','VT',0,NULL,50),(2,'Room B','McBryde','202','VT',0,NULL,40),(3,'Room C','Torg','303','VT',0,NULL,60),(4,'Zoom','Online',NULL,NULL,1,'zoom.com/123',100),(5,'Room D','Holden','404','VT',0,NULL,30);
/*!40000 ALTER TABLE `location` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `membership`
--

DROP TABLE IF EXISTS `membership`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `membership` (
  `StudentID` int NOT NULL,
  `OrgID` int NOT NULL,
  `JoinDate` date NOT NULL,
  `LeaveDate` date DEFAULT NULL,
  `MemberRole` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`StudentID`,`OrgID`),
  KEY `OrgID` (`OrgID`),
  CONSTRAINT `membership_ibfk_1` FOREIGN KEY (`StudentID`) REFERENCES `student` (`StudentID`),
  CONSTRAINT `membership_ibfk_2` FOREIGN KEY (`OrgID`) REFERENCES `organization` (`OrgID`),
  CONSTRAINT `membership_chk_1` CHECK (((`LeaveDate` is null) or (`JoinDate` <= `LeaveDate`)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `membership`
--

LOCK TABLES `membership` WRITE;
/*!40000 ALTER TABLE `membership` DISABLE KEYS */;
INSERT INTO `membership` VALUES (1,1,'2026-01-01',NULL,'Member'),(2,2,'2026-01-01',NULL,'Member'),(3,3,'2026-01-01',NULL,'Member'),(4,4,'2026-01-01',NULL,'Member'),(5,5,'2026-01-01',NULL,'Member'),(458,2,'2026-04-22',NULL,'Member'),(9065,1,'2026-04-22',NULL,'President'),(906597555,6,'2026-04-21',NULL,'Member');
/*!40000 ALTER TABLE `membership` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `organization`
--

DROP TABLE IF EXISTS `organization`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `organization` (
  `OrgID` int NOT NULL,
  `OrgName` varchar(100) NOT NULL,
  `Description` text,
  `ContactEmail` varchar(100) DEFAULT NULL,
  `OrgStatus` varchar(20) NOT NULL,
  PRIMARY KEY (`OrgID`),
  CONSTRAINT `organization_chk_1` CHECK ((`OrgStatus` in (_utf8mb4'Active',_utf8mb4'Inactive',_utf8mb4'Pending')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `organization`
--

LOCK TABLES `organization` WRITE;
/*!40000 ALTER TABLE `organization` DISABLE KEYS */;
INSERT INTO `organization` VALUES (1,'CS Club','Coding org','cs@vt.edu','Active'),(2,'Finance Club','Finance org','fin@vt.edu','Active'),(3,'AI Society','AI org','ai@vt.edu','Active'),(4,'Gaming Club','Gaming org','game@vt.edu','Active'),(5,'Robotics','Robotics org','robot@vt.edu','Active'),(6,'Board Games','Board game org','BG@vt.edu','Active');
/*!40000 ALTER TABLE `organization` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `organization_officer`
--

DROP TABLE IF EXISTS `organization_officer`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `organization_officer` (
  `StudentID` int NOT NULL,
  `OrgID` int NOT NULL,
  `StartDate` date NOT NULL,
  `RoleTitle` varchar(100) NOT NULL,
  `EndDate` date DEFAULT NULL,
  PRIMARY KEY (`StudentID`,`OrgID`,`StartDate`),
  KEY `OrgID` (`OrgID`),
  CONSTRAINT `organization_officer_ibfk_1` FOREIGN KEY (`StudentID`) REFERENCES `student` (`StudentID`),
  CONSTRAINT `organization_officer_ibfk_2` FOREIGN KEY (`OrgID`) REFERENCES `organization` (`OrgID`),
  CONSTRAINT `organization_officer_chk_1` CHECK (((`EndDate` is null) or (`StartDate` <= `EndDate`)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `organization_officer`
--

LOCK TABLES `organization_officer` WRITE;
/*!40000 ALTER TABLE `organization_officer` DISABLE KEYS */;
INSERT INTO `organization_officer` VALUES (1,1,'2026-01-01','President',NULL),(2,2,'2026-01-01','President',NULL),(3,3,'2026-01-01','President',NULL),(4,4,'2026-01-01','President',NULL),(5,5,'2026-01-01','President',NULL),(9065,1,'2026-04-22','President',NULL);
/*!40000 ALTER TABLE `organization_officer` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `registration`
--

DROP TABLE IF EXISTS `registration`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `registration` (
  `StudentID` int NOT NULL,
  `EventID` int NOT NULL,
  `RegisteredAt` datetime NOT NULL,
  `RegistrationStatus` varchar(20) NOT NULL,
  PRIMARY KEY (`StudentID`,`EventID`),
  KEY `EventID` (`EventID`),
  CONSTRAINT `registration_ibfk_1` FOREIGN KEY (`StudentID`) REFERENCES `student` (`StudentID`),
  CONSTRAINT `registration_ibfk_2` FOREIGN KEY (`EventID`) REFERENCES `event` (`EventID`),
  CONSTRAINT `registration_chk_1` CHECK ((`RegistrationStatus` in (_utf8mb4'Registered',_utf8mb4'Waitlisted',_utf8mb4'Cancelled')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `registration`
--

LOCK TABLES `registration` WRITE;
/*!40000 ALTER TABLE `registration` DISABLE KEYS */;
INSERT INTO `registration` VALUES (1,1,'2026-04-02 15:47:29','Registered'),(1,1234,'2026-04-02 17:32:53','Registered'),(2,2,'2026-08-25 10:05:00','Registered'),(3,3,'2026-08-25 10:10:00','Registered'),(4,4,'2026-08-25 10:15:00','Registered'),(5,5,'2026-08-25 10:20:00','Registered'),(458,2,'2026-04-22 17:30:37','Registered'),(9065,1,'2026-04-21 23:57:04','Registered'),(9065,1234,'2026-04-21 23:56:57','Registered'),(12345,1234,'2026-04-21 01:22:11','Registered'),(90673,1,'2026-04-01 03:25:36','Registered'),(90673,4,'2026-04-01 03:25:52','Registered'),(906597555,1,'2026-04-03 00:54:01','Registered'),(906597555,2,'2026-04-02 16:58:07','Registered'),(906597555,1234,'2026-04-02 17:32:28','Cancelled'),(906618852,1,'2026-04-02 17:24:04','Registered');
/*!40000 ALTER TABLE `registration` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `student`
--

DROP TABLE IF EXISTS `student`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `student` (
  `StudentID` int NOT NULL,
  `FirstName` varchar(50) NOT NULL,
  `LastName` varchar(50) NOT NULL,
  `Email` varchar(100) NOT NULL,
  `ClassYear` varchar(20) DEFAULT NULL,
  `Major` varchar(100) DEFAULT NULL,
  `AccountStatus` varchar(20) NOT NULL,
  PRIMARY KEY (`StudentID`),
  UNIQUE KEY `Email` (`Email`),
  CONSTRAINT `student_chk_1` CHECK ((`AccountStatus` in (_utf8mb4'Active',_utf8mb4'Inactive',_utf8mb4'Suspended')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `student`
--

LOCK TABLES `student` WRITE;
/*!40000 ALTER TABLE `student` DISABLE KEYS */;
INSERT INTO `student` VALUES (1,'Brad','Fisher','brad@vt.edu','Senior','CS','Active'),(2,'Alex','Kim','alex@vt.edu','Junior','IT','Active'),(3,'Sam','Lee','sam@vt.edu','Senior','Math','Active'),(4,'Jordan','Miles','jordan@vt.edu','Sophomore','CS','Active'),(5,'Taylor','Nguyen','taylor@vt.edu','Senior','Business','Active'),(6,'Casey','Morgan','casey@vt.edu','Junior','Data Centric Computing','Active'),(7,'Reid','Howe','reid@vt.edu','Junior','CS','Active'),(458,'Jay','Coleman','jcole@vt.edu','2028','BIT','Active'),(9065,'Brad','Fisher','bradf@vt.edu','2027','Computer Science','Active'),(12345,'Rick','Sorken','Rsorken@vt.edu','2027','Computer Science','Active'),(90673,'Jack ','Kama','jkam@vt.edu','2026','BIT','Active'),(906597555,'Bradley','Fisher','bradleyf23@vt.edu','Junior','CS','Active'),(906618852,'Surafail','Asheber','surafail2a@vt.edu','Junior','CS','Active');
/*!40000 ALTER TABLE `student` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-04-23 16:24:38
