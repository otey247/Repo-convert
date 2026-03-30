import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';

test('renders Repo-convert title', () => {
  render(<App />);
  expect(screen.getByText('Repo-convert')).toBeInTheDocument();
});

test('renders app subtitle', () => {
  render(<App />);
  expect(
    screen.getByText(/Convert repository Markdown files to plain text/i)
  ).toBeInTheDocument();
});

test('renders Convert Repository button', () => {
  render(<App />);
  expect(screen.getByRole('button', { name: /Convert Repository/i })).toBeInTheDocument();
});
