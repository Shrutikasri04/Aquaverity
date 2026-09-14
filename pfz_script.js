<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Page Not Found</title>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    body {
      height: 100vh;
      /* background: url('https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1920&q=80') no-repeat center center/cover; -*/
      background: url('/images/banner/background.avif') no-repeat center center/cover;
      font-family: 'Segoe UI', sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-direction: column;
      color: #fff;
      text-align: center;
    }
img {
      max-width: 500px;
      margin-bottom: 50px;
    }
    h1 {
      font-size: 2rem;
      margin-bottom: 20px;
      text-shadow: 2px 2px 4px rgba(0,0,0,0.6);
    }

    .home-btn {
      background-color: rgba(0, 123, 255, 0.8);
      padding: 12px 24px;
      border: none;
      border-radius: 25px;
      color: #fff;
      font-size: 1rem;
      cursor: pointer;
      text-decoration: none;
      transition: background 0.3s ease;
    }

    .home-btn:hover {
      background-color: rgba(0, 123, 255, 1);
    }
  </style>
</head>
<body>
  <img src="/images/banner/emblem-dark.png" style="width:150px;height:150px" alt="INCOIS Logo" />
  <h1>The page you're looking for is not here</h1>
  <a href="https://incois.gov.in" class="home-btn">Go Home</a>
</body>
</html>
