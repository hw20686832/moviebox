-- phpMyAdmin SQL Dump
-- version 4.0.10deb1
-- http://www.phpmyadmin.net
--
-- 主机: localhost
-- 生成日期: 2016-06-16 14:45:57
-- 服务器版本: 5.5.38-0ubuntu0.14.04.1
-- PHP 版本: 5.5.9-1ubuntu4.18

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;

--
-- 数据库: `moviebox`
--
CREATE DATABASE IF NOT EXISTS `moviebox` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
USE `moviebox`;

-- --------------------------------------------------------

--
-- 表的结构 `actor`
--

DROP TABLE IF EXISTS `actor`;
CREATE TABLE IF NOT EXISTS `actor` (
  `id` int(11) NOT NULL,
  `bind_id` int(11) NOT NULL,
  KEY `index_id` (`id`),
  KEY `index_bind_id` (`bind_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='演员关联表';

-- --------------------------------------------------------

--
-- 表的结构 `actor_trans`
--

DROP TABLE IF EXISTS `actor_trans`;
CREATE TABLE IF NOT EXISTS `actor_trans` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `imdb_id` varchar(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `dupe_imdb` (`imdb_id`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 COMMENT='演员信息表' AUTO_INCREMENT=16148 ;

-- --------------------------------------------------------

--
-- 表的结构 `app_upgrade`
--

DROP TABLE IF EXISTS `app_upgrade`;
CREATE TABLE IF NOT EXISTS `app_upgrade` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `url` varchar(200) NOT NULL,
  `md5` varchar(32) NOT NULL,
  `version_code` int(11) NOT NULL,
  `upgrade_info` varchar(2000) NOT NULL,
  `release_time` datetime NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 COMMENT='自升级信息' AUTO_INCREMENT=3 ;

-- --------------------------------------------------------

--
-- 表的结构 `category`
--

DROP TABLE IF EXISTS `category`;
CREATE TABLE IF NOT EXISTS `category` (
  `media_type` int(2) NOT NULL COMMENT '资源类型',
  `id` int(11) NOT NULL COMMENT '关联的分类ID',
  `bind_id` int(8) NOT NULL COMMENT '被关联的对象',
  KEY `index_id` (`id`),
  KEY `index_bind_id` (`bind_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- 表的结构 `category_trans`
--

DROP TABLE IF EXISTS `category_trans`;
CREATE TABLE IF NOT EXISTS `category_trans` (
  `id` int(5) NOT NULL,
  `text_name` varchar(20) NOT NULL COMMENT '分类名',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- 表的结构 `director`
--

DROP TABLE IF EXISTS `director`;
CREATE TABLE IF NOT EXISTS `director` (
  `id` int(11) NOT NULL,
  `bind_id` int(11) NOT NULL,
  KEY `index_id` (`id`),
  KEY `index_bind_id` (`bind_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='导演关联表';

-- --------------------------------------------------------

--
-- 表的结构 `director_trans`
--

DROP TABLE IF EXISTS `director_trans`;
CREATE TABLE IF NOT EXISTS `director_trans` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `imdb_id` varchar(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `dupe_imdb` (`imdb_id`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 COMMENT='导演信息' AUTO_INCREMENT=5858 ;

-- --------------------------------------------------------

--
-- 表的结构 `distributor`
--

DROP TABLE IF EXISTS `distributor`;
CREATE TABLE IF NOT EXISTS `distributor` (
  `id` int(11) NOT NULL,
  `bind_id` int(11) NOT NULL,
  KEY `index_id` (`id`),
  KEY `index_bind_id` (`bind_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='发行商关联表';

-- --------------------------------------------------------

--
-- 表的结构 `distributor_trans`
--

DROP TABLE IF EXISTS `distributor_trans`;
CREATE TABLE IF NOT EXISTS `distributor_trans` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `imdb_id` varchar(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `dupe_imdb` (`imdb_id`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 COMMENT='发行商信息表' AUTO_INCREMENT=12740 ;

-- --------------------------------------------------------

--
-- 表的结构 `movie`
--

DROP TABLE IF EXISTS `movie`;
CREATE TABLE IF NOT EXISTS `movie` (
  `id` int(8) NOT NULL,
  `title` varchar(50) NOT NULL COMMENT '标题',
  `description` varchar(500) DEFAULT NULL COMMENT '描述',
  `play_time` varchar(20) DEFAULT NULL COMMENT '播放时长',
  `release_time` datetime DEFAULT NULL COMMENT '上映时间(US)',
  `year` varchar(8) DEFAULT NULL COMMENT '年份',
  `poster` varchar(200) DEFAULT NULL COMMENT '海报',
  `rating` int(10) DEFAULT '0' COMMENT '评分(累计下载/播放)',
  `imdb_id` varchar(30) DEFAULT NULL COMMENT 'IMDB编号',
  `imdb_rating` varchar(10) DEFAULT NULL COMMENT 'IMDB评分',
  `is_deleted` tinyint(1) DEFAULT '0' COMMENT '删除标识',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- 表的结构 `recommend`
--

DROP TABLE IF EXISTS `recommend`;
CREATE TABLE IF NOT EXISTS `recommend` (
  `id` int(11) NOT NULL COMMENT '关联的对象',
  `bind_id` int(8) NOT NULL COMMENT '被关联的对象',
  UNIQUE KEY `uni_duper` (`id`,`bind_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- 表的结构 `test`
--

DROP TABLE IF EXISTS `test`;
CREATE TABLE IF NOT EXISTS `test` (
  `id` int(5) NOT NULL AUTO_INCREMENT,
  `title` varchar(50) NOT NULL,
  `content` varchar(300) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 AUTO_INCREMENT=9 ;

-- --------------------------------------------------------

--
-- 表的结构 `trailer`
--

DROP TABLE IF EXISTS `trailer`;
CREATE TABLE IF NOT EXISTS `trailer` (
  `id` int(8) NOT NULL,
  `title` varchar(100) DEFAULT NULL COMMENT '标题',
  `description` varchar(2000) DEFAULT NULL COMMENT '描述',
  `poster` varchar(200) DEFAULT NULL COMMENT '海报',
  `rating` int(10) DEFAULT NULL COMMENT '评分(累计下载/播放量)',
  `poster_hires` varchar(200) DEFAULT NULL,
  `release_time` datetime DEFAULT NULL COMMENT '发布信息',
  `is_deleted` tinyint(1) DEFAULT '0' COMMENT '删除标识',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- 表的结构 `trailer_source`
--

DROP TABLE IF EXISTS `trailer_source`;
CREATE TABLE IF NOT EXISTS `trailer_source` (
  `id` int(8) NOT NULL,
  `trailer_id` int(8) NOT NULL COMMENT '预告片ID',
  `create_date` varchar(50) DEFAULT NULL COMMENT '发布时间',
  `link` varchar(100) DEFAULT NULL COMMENT '源链接?',
  `is_deleted` tinyint(1) DEFAULT '0' COMMENT '删除标识',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uni_duper` (`id`,`trailer_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- 表的结构 `tv`
--

DROP TABLE IF EXISTS `tv`;
CREATE TABLE IF NOT EXISTS `tv` (
  `id` int(8) NOT NULL,
  `title` varchar(200) DEFAULT NULL COMMENT '标题',
  `description` varchar(500) DEFAULT NULL COMMENT '描述',
  `poster` varchar(200) DEFAULT NULL COMMENT '海报',
  `rating` int(10) DEFAULT NULL COMMENT '评分(累计下载/播放量)',
  `banner` varchar(200) DEFAULT NULL COMMENT '横幅',
  `banner_mini` varchar(200) DEFAULT NULL COMMENT '横幅(mini)',
  `imdb_id` varchar(20) DEFAULT NULL COMMENT 'IMDB编号',
  `imdb_rating` varchar(20) DEFAULT NULL COMMENT 'IMDB评分',
  `is_deleted` tinyint(1) DEFAULT '0' COMMENT '删除标识',
  `release_time` datetime DEFAULT NULL,
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `delete_filter` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- 表的结构 `tv_episode`
--

DROP TABLE IF EXISTS `tv_episode`;
CREATE TABLE IF NOT EXISTS `tv_episode` (
  `id` int(8) NOT NULL AUTO_INCREMENT,
  `tv_id` int(5) NOT NULL COMMENT '剧ID',
  `season_id` int(5) NOT NULL COMMENT '季(部)ID',
  `description` varchar(500) DEFAULT NULL COMMENT '描述',
  `title` varchar(200) DEFAULT NULL COMMENT '标题',
  `pic` varchar(200) DEFAULT NULL COMMENT '截图',
  `is_deleted` tinyint(1) DEFAULT '0' COMMENT '删除标识',
  `seq` int(4) NOT NULL COMMENT '集序号',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uni_duper` (`tv_id`,`season_id`,`seq`),
  KEY `delete_filter` (`is_deleted`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 AUTO_INCREMENT=144648 ;

-- --------------------------------------------------------

--
-- 表的结构 `tv_season`
--

DROP TABLE IF EXISTS `tv_season`;
CREATE TABLE IF NOT EXISTS `tv_season` (
  `id` int(8) NOT NULL AUTO_INCREMENT,
  `tv_id` int(5) NOT NULL COMMENT '剧ID',
  `banner` varchar(200) DEFAULT NULL COMMENT '横幅',
  `description` varchar(2000) DEFAULT NULL COMMENT '季描述',
  `is_deleted` tinyint(1) DEFAULT '0' COMMENT '删除标识',
  `seq` int(4) NOT NULL COMMENT '季序号',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uni_duper` (`tv_id`,`seq`),
  KEY `delete_filter` (`is_deleted`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 AUTO_INCREMENT=9172 ;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
